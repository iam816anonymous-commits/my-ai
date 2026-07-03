import logging
import time
import psutil
import os
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TaskID
from datetime import datetime
from typing import Dict, Any, List
from web_research_agent.config import (
    LOGS_DIR, OUTPUT_DIR, MAX_ITERATIONS, MAX_SEARCH_RESULTS,
    CONCURRENCY, TRACE_MODE, CONFIDENCE_THRESHOLD
)
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_all
from web_research_agent.tools.extractor import extract_all
from web_research_agent.tools.summarizer import summarize_article
from web_research_agent.tools.reporter import generate_final_report, export_report
from web_research_agent.tools.planner import generate_research_plan
from web_research_agent.tools.reasoner import evaluate_research, update_knowledge_base, calculate_explainable_confidence
from web_research_agent.tools.trace import save_trace_artifacts
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchState, ArticleSummary, EvidenceGraph

# Setup logging
logging.basicConfig(
    filename=LOGS_DIR / "research.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
console = Console()

class ResearchAgent:
    def __init__(self):
        self.llm_client = LLMClient()

    def run(self, query: str):
        state = ResearchState(query=query)
        console.print(f"[bold blue]Initiating Analyst Research Platform[/bold blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:

            # 1. Planning
            task_plan = progress.add_task("[yellow]Planning Stage", total=100)
            t_start = time.time()
            state.plan = generate_research_plan(query, self.llm_client)
            progress.update(task_plan, completed=100)
            state.profiling.stages["planning"] = time.time() - t_start

            # 2. Iterative Research Loop
            loop_total = MAX_ITERATIONS
            task_loop = progress.add_task("[green]Research Cycles", total=loop_total)

            while state.iterations < MAX_ITERATIONS:
                state.iterations += 1
                cycle_prefix = f"Cycle {state.iterations}: "

                current_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
                if not current_queries: break

                # Search
                progress.update(task_loop, description=f"[green]{cycle_prefix}Searching...")
                t_sub = time.time()
                scored_results, rejected = search_web(current_queries, max_results_total=5)
                state.urls_found += (len(scored_results) + len(rejected))
                state.urls_rejected.extend(rejected)

                new_urls = [s["url"] for s in scored_results if s["url"] not in state.sources_collected]
                state.sources_collected.extend(new_urls)
                state.profiling.stages[f"search_iter_{state.iterations}"] = time.time() - t_sub

                if not new_urls: break

                # Fetch & Extract
                progress.update(task_loop, description=f"[green]{cycle_prefix}Fetching sources...")
                t_sub = time.time()
                html_map = fetch_all(new_urls, max_workers=CONCURRENCY)
                state.successful_downloads += sum(1 for h in html_map.values() if h)

                texts_map = extract_all({u: h for u, h in html_map.items() if h})
                valid_texts = {u: t for u, t in texts_map.items() if t}
                state.successful_extractions += len(valid_texts)
                state.profiling.stages[f"extraction_iter_{state.iterations}"] = time.time() - t_sub

                # Summarization
                progress.update(task_loop, description=f"[green]{cycle_prefix}Summarizing...")
                iteration_summaries = []
                for url, text in valid_texts.items():
                    summary = summarize_article(text, self.llm_client)
                    s_info = next((s for s in scored_results if s["url"] == url), {"score": 50, "source_type": "Unknown"})

                    article_summary = ArticleSummary(
                        url=url, summary=summary, quality_score=float(s_info["score"]), source_type=s_info["source_type"]
                    )
                    iteration_summaries.append(article_summary)
                    state.summaries.append(article_summary)
                    state.successful_summaries += 1

                state.knowledge_base = update_knowledge_base([], iteration_summaries, state.plan) # KB logic update

                # Reasoning
                progress.update(task_loop, description=f"[green]{cycle_prefix}Reasoning...")
                t_sub = time.time()
                res = evaluate_research(query, state.plan, state.summaries, self.llm_client, state.iterations)

                state.objective_coverage = res.objective_coverage
                state.contradictions.extend(res.contradictions)
                state.follow_up_queries = res.follow_up_queries
                state.evidence_graph = EvidenceGraph(items=res.evidence_items)
                state.gaps = res.gaps

                state.confidence_breakdown = calculate_explainable_confidence(state.model_dump())
                state.confidence_evolution.append(state.confidence_breakdown.overall)
                state.profiling.stages[f"reasoning_iter_{state.iterations}"] = time.time() - t_sub

                progress.update(task_loop, advance=1)

                # Check stopping threshold
                avg_cov = sum(state.objective_coverage.values()) / len(state.objective_coverage) if state.objective_coverage else 0
                if avg_cov >= CONFIDENCE_THRESHOLD and not res.continue_research:
                     break

            # 3. Final Report
            task_report = progress.add_task("[cyan]Synthesizing Report", total=100)
            t_sub = time.time()
            final_content = generate_final_report(
                state.summaries, state.plan, self.llm_client,
                evidence_items=state.evidence_graph.items,
                contradictions=state.contradictions,
                confidence=state.confidence_breakdown,
                gaps=state.gaps
            )

            # Exports
            export_report(final_content, state.plan, state.model_dump())
            progress.update(task_report, completed=100)
            state.profiling.stages["reporting"] = time.time() - t_sub

        # Trace
        if TRACE_MODE:
            save_trace_artifacts(state)

        console.print(f"[bold green]Research complete![/bold green] Report: {OUTPUT_DIR}/report.md")
        self._display_summary(state)

    def _display_summary(self, state: ResearchState):
        runtime = datetime.now() - state.start_time
        table = Table(title="Execution Summary")
        table.add_row("Total Runtime", str(runtime).split('.')[0])
        table.add_row("Final Confidence", f"{state.confidence_breakdown.overall if state.confidence_breakdown else 0}/100")
        table.add_row("Sources Synthesized", str(len(state.summaries)))
        console.print(table)
