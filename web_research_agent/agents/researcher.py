import logging
import time
from rich.console import Console
from rich.table import Table
from datetime import datetime
from web_research_agent.config import LOGS_DIR, OUTPUT_DIR, MAX_ITERATIONS, MAX_SEARCH_RESULTS
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_html
from web_research_agent.tools.extractor import extract_text
from web_research_agent.tools.summarizer import summarize_article
from web_research_agent.tools.reporter import generate_final_report
from web_research_agent.tools.planner import generate_research_plan
from web_research_agent.tools.reasoner import evaluate_research, update_knowledge_base, calculate_confidence
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchState, ArticleSummary

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
        console.print(f"[bold blue]Initiating Professional Research Agent[/bold blue]")
        console.print(f"Topic: [cyan]{query}[/cyan]\n")

        # 1. Planning
        console.print("[yellow]Phase 1: Strategic Planning...[/yellow]")
        state.plan = generate_research_plan(query, self.llm_client)
        console.print(f"Research Objectives defined: {len(state.plan.objectives)}")

        # 2. Iterative Research Loop
        while state.iterations < MAX_ITERATIONS:
            state.iterations += 1
            console.print(f"\n[bold green]Research Cycle {state.iterations}/{MAX_ITERATIONS}[/bold green]")

            current_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
            if not current_queries:
                break

            # Search
            console.print(f"Executing web searches...")
            urls = search_web(current_queries, max_results_total=MAX_SEARCH_RESULTS)
            new_urls = [u for u in urls if u not in state.sources_collected]
            state.urls_found += len(urls)
            state.urls_filtered += (len(urls) - len(new_urls))
            state.sources_collected.extend(new_urls)

            # Process URLs
            iteration_summaries = []
            for url in new_urls:
                state.urls_processed += 1
                console.print(f"Analyzing source: {url}")
                try:
                    html = fetch_html(url)
                    if not html: raise ValueError("Empty response")
                    state.successful_downloads += 1

                    text = extract_text(html)
                    if not text: raise ValueError("Extraction failed")
                    state.successful_extractions += 1

                    summary = summarize_article(text, self.llm_client)
                    if "**Fallback summary" in summary:
                        state.fallback_summaries_used += 1

                    article_summary = ArticleSummary(url=url, summary=summary)
                    iteration_summaries.append(article_summary)
                    state.summaries.append(article_summary)
                    state.successful_summaries += 1
                except Exception as e:
                    logger.warning(f"Source failed {url}: {e}")
                    state.failed_pages.append({"url": url, "reason": str(e)})

            # Update Knowledge Base
            state.knowledge_base = update_knowledge_base(state.knowledge_base, iteration_summaries, state.plan)

            # 3. Reasoning
            console.print("[yellow]Phase 2: Analytical Reasoning...[/yellow]")
            reasoning = evaluate_research(query, state.plan, state.summaries, self.llm_client, state.iterations)

            state.objective_coverage = reasoning.objective_coverage
            state.contradictions.extend(reasoning.contradictions)
            state.follow_up_queries = reasoning.follow_up_queries

            # Recalculate confidence
            state.confidence_score = calculate_confidence(state.model_dump())

            # Print current coverage
            cov_str = ", ".join([f"{obj[:20]}...: {val}%" for obj, val in state.objective_coverage.items()])
            console.print(f"Current Coverage: {cov_str}")

            if not reasoning.continue_research:
                console.print("Objectives satisfied. Moving to synthesis.")
                break

        # 4. Final Reporting
        console.print("\n[yellow]Phase 3: Report Synthesis...[/yellow]")
        report = generate_final_report(
            state.summaries,
            state.plan,
            self.llm_client,
            iterations=state.iterations,
            coverage=state.objective_coverage,
            contradictions=state.contradictions,
            confidence_score=state.confidence_score
        )

        output_file = OUTPUT_DIR / "report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        console.print(f"[bold green]Research Task Complete![/bold green]")
        console.print(f"Report saved to: [cyan]{output_file}[/cyan]")
        self._display_runtime_metrics(state)

    def _display_runtime_metrics(self, state: ResearchState):
        runtime = datetime.now() - state.start_time

        table = Table(title="Research Runtime Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Planner Objectives", str(len(state.plan.objectives)))
        table.add_row("Searches Executed", str(state.iterations * len(state.plan.queries if state.iterations == 1 else [1]))) # Approximation
        table.add_row("URLs Discovered", str(state.urls_found))
        table.add_row("URLs Filtered", str(state.urls_filtered))
        table.add_row("Downloads Succeeded", str(state.successful_downloads))
        table.add_row("Extractions Succeeded", str(state.successful_extractions))
        table.add_row("Summaries Generated", str(state.successful_summaries))
        table.add_row("Fallback Summaries Used", str(state.fallback_summaries_used))
        table.add_row("Reasoning Iterations", str(state.iterations))

        avg_coverage = sum(state.objective_coverage.values()) / len(state.objective_coverage) if state.objective_coverage else 0
        table.add_row("Average Coverage", f"{avg_coverage:.1f}%")
        table.add_row("Final Confidence", f"{state.confidence_score:.1f}/100")
        table.add_row("Total Runtime", str(runtime).split('.')[0])

        console.print("\n")
        console.print(table)
