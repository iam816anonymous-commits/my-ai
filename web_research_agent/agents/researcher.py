import logging
import time
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
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchState, ArticleSummary, EvidenceGraph, SelfEvaluation

logging.basicConfig(filename=LOGS_DIR / "research.log", level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)
console = Console()

class ResearchAgent:
    def __init__(self):
        self.llm_client = LLMClient()

    def run(self, query: str) -> Tuple[ResearchState, SelfEvaluation]:
        state = ResearchState(query=query)
        console.print(f"[bold blue]Production Research Platform[/bold blue] | Query: [cyan]{query}[/cyan]")

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeElapsedColumn(), console=console) as progress:
            # 1. Planning
            t_plan = progress.add_task("[yellow]Planning...", total=100)
            state.plan = generate_research_plan(query, self.llm_client)
            progress.update(t_plan, completed=100)
            state.profiling.stages["planning"] = progress.tasks[t_plan].elapsed or 0.0

            # 2. Loop
            t_loop = progress.add_task("[green]Research Cycles", total=MAX_ITERATIONS)
            while state.iterations < MAX_ITERATIONS:
                state.iterations += 1
                curr_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
                if not curr_queries: break

                # Search & Quality Rank
                progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Searching & Ranking...")
                scored, rejected, health = search_web(curr_queries, MAX_SEARCH_RESULTS)
                state.search_health.update(health)
                state.urls_found += (len(scored) + len(rejected))
                state.urls_rejected.extend(rejected)

                new_sources = [s for s in scored if s["url"] not in state.sources_collected]
                state.sources_collected.extend([s["url"] for s in new_sources])

                if not new_sources: break

                # Smart Fetch & Parallel Extraction
                progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Fetching Top Sources ({len(new_sources)})...")
                html_map = fetch_all([s["url"] for s in new_sources], CONCURRENCY)
                state.successful_downloads += sum(1 for h in html_map.values() if h)
                state.failed_downloads += sum(1 for h in html_map.values() if not h)

                valid_html = {u: h for u, h in html_map.items() if h}
                texts_map = extract_all(valid_html)
                valid_texts = {u: t for u, t in texts_map.items() if t}
                state.successful_extractions += len(valid_texts)

                # Summarization (Sequential for token management)
                progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Processing Content...")
                iteration_summaries = []
                for url, text in valid_texts.items():
                    summary = summarize_article(text, self.llm_client)
                    state.profiling.llm_calls += 1
                    s_info = next((s for s in new_sources if s["url"] == url), {"score": 50, "tier": 5, "source_type": "Unknown"})
                    article_summary = ArticleSummary(url=url, summary=summary, quality_score=float(s_info["score"]), source_tier=s_info["tier"], source_type=s_info["source_type"])
                    iteration_summaries.append(article_summary)
                    state.summaries.append(article_summary)
                    state.successful_summaries += 1

                state.knowledge_base = update_knowledge_base(state.knowledge_base, iteration_summaries, state.plan)

                # Reasoning
                progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Evaluating Evidence...")
                res = evaluate_research(query, state.plan, state.summaries, self.llm_client, state.iterations)
                state.objective_coverage = res.objective_coverage
                state.contradictions.extend(res.contradictions)
                state.follow_up_queries = res.follow_up_queries
                state.evidence_graph = EvidenceGraph(items=res.evidence_items)
                state.gaps = res.gaps
                state.confidence_breakdown = calculate_explainable_confidence(state.model_dump())
                state.confidence_evolution.append(state.confidence_breakdown.overall)

                progress.update(t_loop, advance=1)

                # Intelligent Termination
                avg_cov = sum(state.objective_coverage.values()) / len(state.objective_coverage) if state.objective_coverage else 0
                tier1_count = sum(1 for s in state.summaries if s.source_tier == 1)
                if avg_cov >= CONFIDENCE_THRESHOLD or tier1_count >= EVIDENCE_SATURATION_THRESHOLD:
                    console.print(f"[dim]Evidence saturation reached ({tier1_count} Tier-1 sources, {avg_cov:.0f}% coverage).[/dim]")
                    break

            # 3. Synthesis
            t_report = progress.add_task("[cyan]Synthesis...", total=100)
            final_content = generate_final_report(state.summaries, state.plan, self.llm_client, state.evidence_graph.items, state.contradictions, state.confidence_breakdown, state.gaps)
            evaluation = run_self_evaluation(final_content, state.plan, self.llm_client)
            export_report(final_content, state.plan, state.model_dump())
            progress.update(t_report, completed=100)

        if TRACE_MODE: save_trace_artifacts(state)
        self._display_stats(state, evaluation)
        return state, evaluation

    def _display_stats(self, state, evaluation):
        runtime = datetime.now() - state.start_time
        table = Table(title="Execution Profile", box=None)
        table.add_column("Metric", style="dim"); table.add_column("Value")
        table.add_row("Runtime", str(runtime).split('.')[0])
        table.add_row("LLM Calls", str(state.profiling.llm_calls))
        table.add_row("Confidence", f"{state.confidence_breakdown.overall if state.confidence_breakdown else 0:.1f}/100")
        table.add_row("Grade", f"[bold yellow]{evaluation.overall_grade}[/bold yellow]")
        console.print(table)
