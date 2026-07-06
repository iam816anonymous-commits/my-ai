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
from web_research_agent.tools.reporter import generate_final_report, export_report, run_self_evaluation, validate_objective_completeness
from web_research_agent.tools.planner import generate_research_plan
from web_research_agent.tools.reasoner import evaluate_research, update_knowledge_base, calculate_explainable_confidence
from web_research_agent.tools.trace import save_trace_artifacts
from web_research_agent.tools.storage import storage
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchState, ArticleSummary, EvidenceGraph, SelfEvaluation, ObjectiveState, ObjectiveStatus, PipelineResult

logger = logging.getLogger(__name__)
console = Console()

class ResearchAgent:
    def __init__(self, on_progress=None):
        """
        :param on_progress: Callback function(event_type: str, data: dict)
        """
        self.llm_client = LLMClient()
        self.on_progress = on_progress

    def _emit(self, event_type: str, state: ResearchState):
        if self.on_progress:
            try:
                # Use json mode for WebSocket compatibility (Enums, Datetimes)
                self.on_progress(event_type, state.model_dump(mode='json'))
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def run(self, query: str) -> Tuple[ResearchState, SelfEvaluation]:
        state = ResearchState(query=query, report_id=storage.generate_report_id())
        evaluation = SelfEvaluation(overall_grade="U", justification="Research not completed")
        avg_cov = 0.0

        console.print(f"[bold blue]Production Research Platform[/bold blue] | ID: [magenta]{state.report_id}[/magenta]")

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeElapsedColumn(), console=console) as progress:
                # 1. Planning
                t_plan = progress.add_task("[yellow]Strategizing...", total=100)
                self._emit("planning_start", state)
                state.plan = generate_research_plan(query, self.llm_client)
                for obj in state.plan.objectives:
                    state.objective_states[obj] = ObjectiveState(objective=obj)
                progress.update(t_plan, completed=100)
                state.profiling.stages["planning"] = progress.tasks[t_plan].elapsed or 0.0
                self._emit("planning_complete", state)

                # 2. Research Loop (Adaptive Autonomous Execution)
                t_loop = progress.add_task("[green]Adaptive Cycles", total=MAX_ITERATIONS)
                while state.iterations < MAX_ITERATIONS:
                    state.iterations += 1

                    # Live Research Dashboard Stats
                    active_obj = [o for o in state.objective_states.values() if o.status != ObjectiveStatus.COMPLETE]
                    completed_count = len(state.objective_states) - len(active_obj)

                    self._emit("iteration_start", state)
                    curr_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
                    if not curr_queries: break

                    # Search (Avoid redundant queries)
                    progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Searching...")
                    state.report_status = "searching"
                    self._emit("search_start", state)

                    # Filter out queries we've tried too many times
                    fresh_queries = [q for q in curr_queries if q not in state.follow_up_queries or state.iterations < 2]
                    if not fresh_queries: fresh_queries = curr_queries[:2]

                    start_search = time.time()
                    search_res = search_web(fresh_queries, MAX_SEARCH_RESULTS)
                    if not search_res.success:
                         logger.error(f"Search failed: {search_res.errors}")
                         continue

                    scored, rejected, health = search_res.payload
                    state.search_health.update(health)
                    state.urls_found += (len(scored) + len(rejected))
                    state.urls_rejected.extend(rejected)

                    # Memory: Avoid revisiting URLs
                    new_urls = [s["url"] for s in scored if s["url"] not in state.visited_urls and s["url"] not in state.failed_fetches]
                    state.sources_collected.extend([u for u in new_urls if u not in state.sources_collected])
                    state.profiling.stages[f"search_iter_{state.iterations}"] = time.time() - start_search
                    self._emit("search_complete", state)

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
                    state.report_status = "fetching"
                    self._emit("fetch_start", state)
                    start_fetch = time.time()
                    html_map, latency = fetch_all(new_urls, CONCURRENCY)
                    state.profiling.http_latency += latency

                    # Update Memory & Trace
                    for url, html in html_map.items():
                        logger.info(f"Pipeline Trace [{state.report_id}]: URL discovered: {url}")
                        if html:
                            logger.info(f"Pipeline Trace [{state.report_id}]: URL fetched successfully: {url}")
                            state.visited_urls.append(url)
                            state.successful_downloads += 1
                        else:
                            logger.warning(f"Pipeline Trace [{state.report_id}]: URL fetch failed: {url}")
                            state.failed_fetches.append(url)
                            state.failed_downloads += 1

                    extract_res = extract_all({u: h for u, h in html_map.items() if h}, state.query, self.llm_client)
                    if not extract_res.success:
                         logger.error(f"Extraction failed: {extract_res.errors}")
                         continue

                    texts_map = extract_res.payload
                    valid_texts = {u: t for u, t in texts_map.items() if t}
                    for u in valid_texts:
                         logger.info(f"Pipeline Trace [{state.report_id}]: Content extracted and validated: {u}")
                    state.successful_extractions += len(valid_texts)
                    state.profiling.stages[f"fetch_iter_{state.iterations}"] = time.time() - start_fetch
                    self._emit("fetch_complete", state)

                    # Summarize (Parallel)
                    progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Parallel Summarization...")
                    state.report_status = "summarizing"
                    self._emit("summarize_start", state)
                    from concurrent.futures import ThreadPoolExecutor

                    def summarize_and_score(url, text):
                        sum_res = summarize_article(text, self.llm_client, state.query)
                        if not sum_res.success:
                             return None
                        summary = sum_res.payload
                        s_info = next((s for s in scored if s["url"] == url), {"score": 50, "tier": 5, "source_type": "Unknown"})
                        return ArticleSummary(
                            url=url,
                            summary=summary,
                            quality_score=float(s_info["score"]),
                            source_tier=s_info["tier"],
                            source_type=s_info["source_type"]
                        )

                    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
                        results = list(executor.map(lambda x: summarize_and_score(*x), valid_texts.items()))
                        iteration_summaries = [r for r in results if r is not None]

                    for s in iteration_summaries:
                        logger.info(f"Pipeline Trace [{state.report_id}]: Summary generated for {s.url}")

                    state.summaries.extend(iteration_summaries)
                    state.successful_summaries += len(iteration_summaries)
                    self._emit("summarize_complete", state)

                    state.knowledge_base = update_knowledge_base(state.knowledge_base, iteration_summaries, state.plan)
                    logger.info(f"Pipeline Trace [{state.report_id}]: Knowledge base updated with {len(iteration_summaries)} new entries.")

                    # Reasoning
                    progress.update(t_loop, description=f"[green]Cycle {state.iterations}: Evaluating Evidence...")
                    state.report_status = "reasoning"
                    self._emit("reasoning_start", state)
                    start_reason = time.time()
                    reason_res = evaluate_research(query, state.plan, state.summaries, self.llm_client, state.iterations, state.urls_found, state.objective_states)

                    if not reason_res.success:
                         logger.error(f"Reasoning failed: {reason_res.errors}")
                         continue

                    res = reason_res.payload
                    # Update State Machine
                    for os in res.objective_states:
                        state.objective_states[os.objective] = os
                    state.contradictions.extend(res.contradictions)
                    state.follow_up_queries = res.follow_up_queries
                    state.evidence_graph = EvidenceGraph(items=res.evidence_items)
                    state.gaps = res.gaps
                    state.confidence_breakdown = res.confidence_breakdown
                    state.confidence_evolution.append(state.confidence_breakdown.overall)
                    state.profiling.stages[f"reasoning_iter_{state.iterations}"] = time.time() - start_reason
                    self._emit("reasoning_complete", state)

                    progress.update(t_loop, advance=1)
                    avg_cov = sum(o.coverage for o in state.objective_states.values()) / len(state.objective_states)

                    # Autonomous Stopping Decision (Final Decision Step)
                    if not res.continue_research:
                        logger.info(f"Autonomous termination: Agent decided research objectives are satisfied.")
                        break

                    # Fallback stopping logic (Resource exhaustion)
                    if state.iterations >= MAX_ITERATIONS:
                        logger.warning("Terminating research: Maximum cycles reached.")
                        break

                # Synthesis
                t_report = progress.add_task("[cyan]Synthesis...", total=100)
                state.report_status = "synthesizing"
                self._emit("synthesis_start", state)
                final_content = generate_final_report(state.summaries, state.plan, self.llm_client, state.evidence_graph.items, state.contradictions, state.confidence_breakdown, state.gaps)

                # Validation
                progress.update(t_report, description="[cyan]Validating Completeness...")
                state.report_status = "validating"
                completeness = validate_objective_completeness(final_content, state.plan.objectives, self.llm_client)
                for obj, status in completeness.items():
                    if status == "NO" and state.objective_states[obj].status == ObjectiveStatus.COMPLETE:
                         state.objective_states[obj].status = ObjectiveStatus.INSUFFICIENT_EVIDENCE

                evaluation = run_self_evaluation(final_content, state.plan, self.llm_client)
                export_report(final_content, state.plan, state.model_dump(), storage)
                storage.update_index({"id": state.report_id, "query": query, "created_at": datetime.now().isoformat(), "confidence": state.confidence_breakdown.overall, "coverage": round(avg_cov, 1), "grade": evaluation.overall_grade, "runtime": str(datetime.now() - state.start_time).split('.')[0], "report": f"reports/{state.report_id}.md", "trace": f"traces/{state.report_id}.md"})
                progress.update(t_report, completed=100)
                self._emit("synthesis_complete", state)

        except Exception as e:
            logger.exception("Pipeline fatal error")
            self._save_diagnostics(state, e)
            raise e
        finally:
            # Update profiling with LLM usage before saving trace
            state.profiling.prompt_tokens = self.llm_client.total_prompt_tokens
            state.profiling.completion_tokens = self.llm_client.total_completion_tokens
            state.profiling.estimated_cost_usd = self.llm_client.total_cost_usd

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

        # Dashboard Table
        table = Table(title="[bold blue]Autonomous Research Dashboard[/bold blue]", box=None)
        table.add_column("Dimension", style="dim")
        table.add_column("Value")

        avg_cov = sum(o.coverage for o in state.objective_states.values()) / len(state.objective_states)
        table.add_row("Overall Coverage", f"{avg_cov:.1f}%")
        table.add_row("Confidence", f"{state.confidence_breakdown.overall:.1f}/100")
        table.add_row("Evidence Items", f"{len(state.evidence_graph.items)}")
        table.add_row("Sources Collected", f"{len(state.summaries)}")
        table.add_row("Grade", f"[bold yellow]{evaluation.overall_grade}[/bold yellow]")
        table.add_row("Runtime", str(runtime).split('.')[0])
        table.add_row("Peak RAM", f"{process.memory_info().rss / (1024 * 1024):.1f} MB")

        console.print("\n")
        console.print(table)

        # Objective Status Machine View
        obj_table = Table(title="[bold cyan]Objective State Machine[/bold cyan]", box=None)
        obj_table.add_column("Objective", width=40)
        obj_table.add_column("Status")
        obj_table.add_column("Cov %")
        obj_table.add_column("Sources")

        for obj_name, obj in state.objective_states.items():
            status_style = "green" if obj.status == ObjectiveStatus.COMPLETE else "yellow" if obj.status == ObjectiveStatus.SEARCHING else "red"
            obj_table.add_row(
                obj_name,
                f"[{status_style}]{obj.status.value}[/{status_style}]",
                f"{obj.coverage:.0f}%",
                str(obj.number_of_sources)
            )

        console.print("\n")
        console.print(obj_table)
