import logging
import time
import psutil
import os
from rich.console import Console
from rich.table import Table
from datetime import datetime
from typing import Dict, Any
from web_research_agent.config import LOGS_DIR, OUTPUT_DIR, MAX_ITERATIONS, MAX_SEARCH_RESULTS
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_all
from web_research_agent.tools.extractor import extract_all
from web_research_agent.tools.summarizer import summarize_article
from web_research_agent.tools.reporter import generate_final_report, run_self_evaluation
from web_research_agent.tools.planner import generate_research_plan
from web_research_agent.tools.reasoner import evaluate_research, update_knowledge_base, calculate_confidence
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchState, ArticleSummary, EvidenceGraph, SourceQualityStats

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
        logger.info(f"Initiating Research: {query}")
        console.print(f"[bold blue]Initiating Analyst-Grade Research Agent[/bold blue]")

        # 1. Planning
        t_start = time.time()
        console.print("[yellow]Phase 1: Analytical Planning...[/yellow]")
        state.plan = generate_research_plan(query, self.llm_client)
        state.profiling.slowest_functions["planning"] = time.time() - t_start

        # 2. Iterative Research Loop
        while state.iterations < MAX_ITERATIONS:
            state.iterations += 1
            console.print(f"\n[bold green]Research Cycle {state.iterations}/{MAX_ITERATIONS}[/bold green]")

            current_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
            if not current_queries: break

            # Search
            t_sub = time.time()
            scored_sources = search_web(current_queries, max_results_total=5)
            urls = [s["url"] for s in scored_sources]
            new_urls = [u for u in urls if u not in state.sources_collected]
            state.urls_found += len(urls)
            state.urls_filtered += (len(urls) - len(new_urls))
            state.sources_collected.extend(new_urls)
            state.profiling.slowest_functions[f"search_iter_{state.iterations}"] = time.time() - t_sub

            # Update Source Stats
            for s in scored_sources:
                stype = s["source_type"]
                state.source_stats.type_counts[stype] = state.source_stats.type_counts.get(stype, 0) + 1

            # Parallel Fetch & Extraction
            t_sub = time.time()
            html_contents = fetch_all(new_urls)
            state.successful_downloads += sum(1 for h in html_contents.values() if h)
            state.profiling.download_times.append(time.time() - t_sub)

            t_sub = time.time()
            extracted_texts = extract_all({u: h for u, h in html_contents.items() if h})
            valid_texts = {u: t for u, t in extracted_texts.items() if t}
            state.successful_extractions += len(valid_texts)
            state.profiling.extraction_times.append(time.time() - t_sub)

            # Summarization
            iteration_summaries = []
            for url, text in valid_texts.items():
                try:
                    summary = summarize_article(text, self.llm_client)
                    if "**Fallback summary" in summary: state.fallback_summaries_used += 1

                    # Find source info for quality score
                    s_info = next((s for s in scored_sources if s["url"] == url), {"score": 50, "source_type": "Unknown"})

                    article_summary = ArticleSummary(
                        url=url,
                        summary=summary,
                        quality_score=float(s_info["score"]),
                        source_type=s_info["source_type"]
                    )
                    iteration_summaries.append(article_summary)
                    state.summaries.append(article_summary)
                    state.successful_summaries += 1
                except Exception as e:
                    logger.warning(f"Summarization failed for {url}: {e}")

            # Reasoning
            t_sub = time.time()
            reasoning = evaluate_research(query, state.plan, state.summaries, self.llm_client, state.iterations)
            state.objective_coverage = reasoning.objective_coverage
            state.contradictions.extend(reasoning.contradictions)
            state.follow_up_queries = reasoning.follow_up_queries
            state.evidence_graph = EvidenceGraph(items=reasoning.evidence_items)
            state.confidence_score = calculate_confidence(state.model_dump())
            state.profiling.slowest_functions[f"reasoning_iter_{state.iterations}"] = time.time() - t_sub

            if not reasoning.continue_research: break

        # 4. Final Reporting
        t_sub = time.time()
        report_content = generate_final_report(
            state.summaries, state.plan, self.llm_client,
            evidence_items=state.evidence_graph.items,
            contradictions=state.contradictions,
            confidence_score=state.confidence_score
        )
        state.profiling.slowest_functions["reporting"] = time.time() - t_sub

        evaluation = run_self_evaluation(report_content, state.plan, self.llm_client)

        # Save output
        output_file = OUTPUT_DIR / "report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
            f.write("\n\n----- # Quality Audit\nGrade: " + evaluation.overall_grade + "\n" + evaluation.justification)

        self._display_runtime_metrics(state, evaluation)
        return state, evaluation

    def _display_runtime_metrics(self, state: ResearchState, evaluation):
        runtime = datetime.now() - state.start_time
        process = psutil.Process(os.getpid())
        peak_mem = process.memory_info().rss / (1024 * 1024)

        table = Table(title="Research Performance Metrics")
        table.add_row("Total Runtime", str(runtime).split('.')[0])
        table.add_row("Peak RAM", f"{peak_mem:.1f} MB")
        table.add_row("Avg Coverage", f"{sum(state.objective_coverage.values())/len(state.objective_coverage):.0f}%" if state.objective_coverage else "0%")
        table.add_row("Final Confidence", f"{state.confidence_score:.1f}/100")
        table.add_row("Audit Grade", evaluation.overall_grade)
        console.print(table)
