import logging
from rich.console import Console
from rich.table import Table
from datetime import datetime
from web_research_agent.config import LOGS_DIR, OUTPUT_DIR, MAX_ITERATIONS, MAX_SEARCH_RESULTS
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_all
from web_research_agent.tools.extractor import extract_all
from web_research_agent.tools.summarizer import summarize_article
from web_research_agent.tools.reporter import generate_final_report, run_self_evaluation
from web_research_agent.tools.planner import generate_research_plan
from web_research_agent.tools.reasoner import evaluate_research, update_knowledge_base, calculate_confidence
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
        console.print(f"[bold blue]Initiating Analyst-Grade Research Agent[/bold blue]")
        console.print(f"Query: [cyan]{query}[/cyan]\n")

        # 1. Planning
        console.print("[yellow]Phase 1: Analytical Planning...[/yellow]")
        state.plan = generate_research_plan(query, self.llm_client)
        console.print(f"Intent: [bold magenta]{state.plan.intent}[/bold magenta]")
        console.print(f"Objectives: {len(state.plan.objectives)}")

        # 2. Iterative Research Loop
        while state.iterations < MAX_ITERATIONS:
            state.iterations += 1
            console.print(f"\n[bold green]Research Cycle {state.iterations}/{MAX_ITERATIONS}[/bold green]")

            current_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
            if not current_queries: break

            # Search
            console.print(f"Searching web...")
            urls = search_web(current_queries, max_results_total=MAX_SEARCH_RESULTS)
            new_urls = [u for u in urls if u not in state.sources_collected]
            state.urls_found += len(urls)
            state.urls_filtered += (len(urls) - len(new_urls))
            state.sources_collected.extend(new_urls)

            if not new_urls:
                console.print("No new unique sources discovered.")

            # Parallel Parallel Processing (Phase 2 & 3)
            console.print(f"Parallel Fetch & Extraction ({len(new_urls)} sources)...")
            html_contents = fetch_all(new_urls)
            # Remove empty ones
            valid_html = {u: h for u, h in html_contents.items() if h}
            state.successful_downloads += len(valid_html)

            extracted_texts = extract_all(valid_html)
            valid_texts = {u: t for u, t in extracted_texts.items() if t}
            state.successful_extractions += len(valid_texts)

            # Summarization (Sequential for controlled LLM concurrency/rate limits)
            iteration_summaries = []
            for url, text in valid_texts.items():
                console.print(f"Summarizing: {url}")
                try:
                    summary = summarize_article(text, self.llm_client)
                    if "**Fallback summary" in summary:
                        state.fallback_summaries_used += 1

                    article_summary = ArticleSummary(url=url, summary=summary)
                    iteration_summaries.append(article_summary)
                    state.summaries.append(article_summary)
                    state.successful_summaries += 1
                except Exception as e:
                    logger.warning(f"Summarization failed for {url}: {e}")

            # Update Knowledge
            state.knowledge_base = update_knowledge_base(state.knowledge_base, iteration_summaries, state.plan)

            # Reasoning
            console.print("[yellow]Reasoning & Evidence Mapping...[/yellow]")
            reasoning = evaluate_research(query, state.plan, state.summaries, self.llm_client, state.iterations)

            state.objective_coverage = reasoning.objective_coverage
            state.contradictions.extend(reasoning.contradictions)
            state.follow_up_queries = reasoning.follow_up_queries
            state.evidence_graph = EvidenceGraph(items=reasoning.evidence_items)

            state.confidence_score = calculate_confidence(state.model_dump())

            avg_cov = sum(state.objective_coverage.values()) / len(state.objective_coverage) if state.objective_coverage else 0
            console.print(f"Cycle Coverage: [bold cyan]{avg_cov:.0f}%[/bold cyan] | Confidence: [bold cyan]{state.confidence_score:.0f}/100[/bold cyan]")

            if not reasoning.continue_research:
                console.print("Objectives satisfied. Advancing to synthesis.")
                break

        # 4. Final Reporting
        console.print("\n[yellow]Phase 3: Cross-Source Synthesis...[/yellow]")
        report_content = generate_final_report(
            state.summaries,
            state.plan,
            self.llm_client,
            evidence_items=state.evidence_graph.items,
            contradictions=state.contradictions,
            confidence_score=state.confidence_score
        )

        # Self-Evaluation
        console.print("[yellow]Phase 4: Quality Audit...[/yellow]")
        evaluation = run_self_evaluation(report_content, state.plan, self.llm_client)

        # Save
        output_file = OUTPUT_DIR / "report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
            f.write("\n\n---\n")
            f.write(f"# Quality Audit\nGrade: {evaluation.overall_grade}\n{evaluation.justification}")

        console.print(f"[bold green]Report Synthesized![/bold green] Grade: [bold yellow]{evaluation.overall_grade}[/bold yellow]")
        self._display_runtime_metrics(state, evaluation)

    def _display_runtime_metrics(self, state: ResearchState, evaluation):
        runtime = datetime.now() - state.start_time

        table = Table(title="Research Runtime Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Planner Objectives", str(len(state.plan.objectives)))
        table.add_row("Searches Executed", str(state.iterations * 5)) # approx
        table.add_row("URLs Discovered", str(state.urls_found))
        table.add_row("URLs Filtered", str(state.urls_filtered))
        table.add_row("Downloads Succeeded", str(state.successful_downloads))
        table.add_row("Extractions Succeeded", str(state.successful_extractions))
        table.add_row("Summaries Generated", str(state.successful_summaries))
        table.add_row("Fallback Summaries Used", str(state.fallback_summaries_used))
        table.add_row("Reasoning Iterations", str(state.iterations))

        avg_coverage = sum(state.objective_coverage.values()) / len(state.objective_coverage) if state.objective_coverage else 0
        table.add_row("Final Coverage", f"{avg_coverage:.0f}%")
        table.add_row("Final Confidence", f"{state.confidence_score:.1f}/100")
        table.add_row("Quality Audit Grade", evaluation.overall_grade)
        table.add_row("Total Runtime", str(runtime).split('.')[0])

        console.print("\n")
        console.print(table)
