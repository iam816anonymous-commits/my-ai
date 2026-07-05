import logging
import time
import psutil
import os
import json
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TaskID
from datetime import datetime
from typing import Dict, Any, List, Tuple
from web_research_agent.config import (
    LOGS_DIR, OUTPUT_DIR, MAX_ITERATIONS, MAX_SEARCH_RESULTS,
    CONCURRENCY, TRACE_MODE, CONFIDENCE_THRESHOLD, EVIDENCE_SATURATION_THRESHOLD
)
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_all
from web_research_agent.tools.extractor import extract_all
from web_research_agent.tools.summarizer import summarize_article
from web_research_agent.tools.reporter import generate_final_report, export_report, run_self_evaluation
from web_research_agent.tools.planner import generate_research_plan
from web_research_agent.tools.reasoner import evaluate_research, update_knowledge_base, calculate_explainable_confidence
from web_research_agent.tools.trace import save_trace_artifacts
from web_research_agent.tools.storage import storage
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchState, ArticleSummary, EvidenceGraph, SelfEvaluation, ObjectiveState, PipelineResult

logger = logging.getLogger(__name__)
console = Console()

class ResearchAgent:
    def __init__(self):
        self.llm_client = LLMClient()

    def run(self, query: str) -> Tuple[ResearchState, SelfEvaluation]:
        state = ResearchState(query=query, report_id=storage.generate_report_id())
        evaluation = SelfEvaluation(overall_grade="U", justification="Research not completed")
        avg_cov = 0.0

        console.print(f"[bold blue]Production Research Platform[/bold blue] | ID: [magenta]{state.report_id}[/magenta]")

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeElapsedColumn(), console=console) as progress:
                # 1. Planning
                t_plan = progress.add_task("[yellow]Strategizing...", total=100)
                state.plan = generate_research_plan(query, self.llm_client)
                for obj in state.plan.objectives:
                    state.objective_states[obj] = ObjectiveState(objective=obj)
                progress.update(t_plan, completed=100)
                state.profiling.stages["planning"] = progress.tasks[t_plan].elapsed or 0.0

                # 2. Research Loop
                t_loop = progress.add_task("[green]Evidence Cycles", total=MAX_ITERATIONS)
                while state.iterations < MAX_ITERATIONS:
                    state.iterations += 1
                    curr_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
                    if not curr_queries: break

                    # Search
                    progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Searching...")
                    start_search = time.time()
                    scored, rejected, health = search_web(curr_queries, MAX_SEARCH_RESULTS)
                    state.search_health.update(health)
                    state.urls_found += (len(scored) + len(rejected))
                    state.urls_rejected.extend(rejected)
                    new_urls = [s["url"] for s in scored if s["url"] not in state.sources_collected]
                    state.sources_collected.extend(new_urls)
                    state.profiling.stages[f"search_iter_{state.iterations}"] = time.time() - start_search

                    # TASK 5: Search validation
                    if not new_urls and state.iterations == 1:
                        # CRITICAL: No evidence found on first iteration
                        state.report_status = "failed_no_evidence"
                        error_msg = f"No unique URLs discovered for queries: {curr_queries}"
                        self._save_diagnostics(state, ValueError(error_msg))
                        console.print(f"\n[bold red]ERROR: Evidence collection failed.[/bold red]")
                        console.print(f"[red]{error_msg}[/red]")
                        return state, evaluation

                    if not new_urls: break

                    # TASK 6: Pipeline integrity - ensure evidence exists before proceeding
                    # Fetch & Extract
                    progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Parallel Fetching...")
                    start_fetch = time.time()
                    html_map, latency = fetch_all(new_urls, CONCURRENCY)
                    state.profiling.http_latency += latency
                    state.successful_downloads += sum(1 for h in html_map.values() if h)
                    state.failed_downloads += sum(1 for h in html_map.values() if not h)

                    texts_map = extract_all({u: h for u, h in html_map.items() if h})
                    valid_texts = {u: t for u, t in texts_map.items() if t}
                    state.successful_extractions += len(valid_texts)
                    state.profiling.stages[f"fetch_iter_{state.iterations}"] = time.time() - start_fetch

                    # Summarize
                    iteration_summaries = []
                    for url, text in valid_texts.items():
                        summary = summarize_article(text, self.llm_client)
                        state.profiling.llm_calls += 1
                        s_info = next((s for s in scored if s["url"] == url), {"score": 50, "tier": 5, "source_type": "Unknown"})
                        article_summary = ArticleSummary(url=url, summary=summary, quality_score=float(s_info["score"]), source_tier=s_info["tier"], source_type=s_info["source_type"])
                        iteration_summaries.append(article_summary)
                        state.summaries.append(article_summary)
                        state.successful_summaries += 1

                    state.knowledge_base = update_knowledge_base(state.knowledge_base, iteration_summaries, state.plan)

                    # Reasoning
                    progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Evaluating...")
                    start_reason = time.time()
                    res = evaluate_research(query, state.plan, state.summaries, self.llm_client, state.iterations, state.objective_states)
                    for os in res.objective_states:
                        state.objective_states[os.objective] = os
                    state.contradictions.extend(res.contradictions)
                    state.follow_up_queries = res.follow_up_queries
                    state.evidence_graph = EvidenceGraph(items=res.evidence_items)
                    state.gaps = res.gaps
                    state.confidence_breakdown = res.confidence_breakdown or calculate_explainable_confidence(state.model_dump())
                    state.confidence_evolution.append(state.confidence_breakdown.overall)
                    state.profiling.stages[f"reasoning_iter_{state.iterations}"] = time.time() - start_reason

                    progress.update(t_loop, advance=1)
                    avg_cov = sum(o.coverage for o in state.objective_states.values()) / len(state.objective_states)
                    tier1_count = sum(1 for s in state.summaries if s.source_tier == 1)
                    if avg_cov >= CONFIDENCE_THRESHOLD or tier1_count >= EVIDENCE_SATURATION_THRESHOLD: break

                # Synthesis
                t_report = progress.add_task("[cyan]Synthesis...", total=100)
                final_content = generate_final_report(state.summaries, state.plan, self.llm_client, state.evidence_graph.items, state.contradictions, state.confidence_breakdown, state.gaps)
                evaluation = run_self_evaluation(final_content, state.plan, self.llm_client)
                export_report(final_content, state.plan, state.model_dump(), storage)
                storage.update_index({"id": state.report_id, "query": query, "created_at": datetime.now().isoformat(), "confidence": state.confidence_breakdown.overall, "coverage": round(avg_cov, 1), "grade": evaluation.overall_grade, "runtime": str(datetime.now() - state.start_time).split('.')[0], "report": f"reports/{state.report_id}.md", "trace": f"traces/{state.report_id}.md"})
                progress.update(t_report, completed=100)

        except Exception as e:
            logger.exception("Pipeline fatal error")
            self._save_diagnostics(state, e)
            raise e

        if TRACE_MODE: save_trace_artifacts(state, state.report_id)
        self._display_summary(state, evaluation)
        return state, evaluation

    def _save_diagnostics(self, state, error):
        import traceback
        diag = {
            "report_id": state.report_id,
            "query": state.query,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "stage": state.report_status,
            "timings": state.profiling.stages,
            "iterations": state.iterations,
            "stats": {
                "urls_found": state.urls_found,
                "downloads": state.successful_downloads,
                "extractions": state.successful_extractions,
                "summaries": state.successful_summaries
            }
        }
        with open(OUTPUT_DIR / "pipeline_diagnostics.json", "w") as f:
            json.dump(diag, f, indent=2)

    def _display_summary(self, state, evaluation):
        runtime = datetime.now() - state.start_time
        process = psutil.Process(os.getpid())
        table = Table(title="Execution Profile", box=None)
        table.add_column("Metric", style="dim"); table.add_column("Value")
        table.add_row("Runtime", str(runtime).split('.')[0])
        table.add_row("Confidence", f"{state.confidence_breakdown.overall:.1f}/100")
        table.add_row("Grade", f"[bold yellow]{evaluation.overall_grade}[/bold yellow]")
        table.add_row("Peak RAM", f"{process.memory_info().rss / (1024 * 1024):.1f} MB")
        console.print(table)
