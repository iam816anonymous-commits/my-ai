import logging
from rich.console import Console
from rich.table import Table
from web_research_agent.config import LOGS_DIR, OUTPUT_DIR
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_html
from web_research_agent.tools.extractor import extract_text
from web_research_agent.tools.summarizer import summarize_article
from web_research_agent.tools.reporter import generate_final_report
from web_research_agent.tools.planner import generate_research_plan
from web_research_agent.tools.reasoner import evaluate_research, update_knowledge_base
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
        console.print(f"[bold blue]Initiating Intelligent Research:[/bold blue] {query}")

        # 1. Planning
        console.print("[yellow]Phase: Planning...[/yellow]")
        state.plan = generate_research_plan(query, self.llm_client)

        # 2. Iterative Research Loop
        max_iterations = 3
        while state.iterations < max_iterations:
            state.iterations += 1
            console.print(f"\n[bold green]Cycle {state.iterations}/{max_iterations}[/bold green]")

            # Select queries
            current_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
            if not current_queries:
                logger.info("No queries for current cycle. Stopping.")
                break

            # Multi-search
            console.print(f"Searching...")
            urls = search_web(current_queries, max_results_total=5)
            # Only process new URLs
            new_urls = [u for u in urls if u not in state.sources_collected]
            state.sources_collected.extend(new_urls)
            state.urls_found += len(new_urls)

            if not new_urls:
                console.print("No new unique sources found.")
                # We don't break yet, we might want to reason with what we have

            # Process URLs
            iteration_summaries = []
            for url in new_urls:
                console.print(f"Analyzing: {url}")
                try:
                    html = fetch_html(url)
                    if not html: raise ValueError("Download failed")
                    state.successful_downloads += 1

                    text = extract_text(html)
                    if not text: raise ValueError("Extraction failed")
                    state.successful_extractions += 1

                    summary = summarize_article(text, self.llm_client)
                    article_summary = ArticleSummary(url=url, summary=summary)
                    iteration_summaries.append(article_summary)
                    state.summaries.append(article_summary)
                    state.successful_summaries += 1
                except Exception as e:
                    logger.warning(f"Process failed for {url}: {e}")
                    state.failed_pages.append({"url": url, "reason": str(e)})

            # Update Knowledge
            state.knowledge_base = update_knowledge_base(state.knowledge_base, iteration_summaries, state.plan)

            # 3. Reason & Evaluate
            console.print("[yellow]Phase: Reasoning...[/yellow]")
            reasoning = evaluate_research(query, state.plan, state.summaries, self.llm_client)

            state.objective_coverage = reasoning.objective_coverage
            state.contradictions.extend(reasoning.contradictions)
            state.follow_up_queries = reasoning.follow_up_queries
            state.confidence_score = reasoning.confidence / 100.0

            # Exit Conditions
            if not reasoning.continue_research:
                console.print("Research objectives satisfied.")
                break

            if all(cov >= 90 for cov in state.objective_coverage.values()):
                console.print("Sufficient coverage achieved.")
                break

        # 4. Final Reporting
        console.print("[yellow]Phase: Reporting...[/yellow]")
        report = generate_final_report(
            state.summaries,
            state.plan,
            self.llm_client,
            iterations=state.iterations,
            coverage=state.objective_coverage,
            contradictions=state.contradictions
        )

        # Save output
        output_file = OUTPUT_DIR / "report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        console.print(f"[bold green]Task Complete![/bold green] Results in {output_file}")
        self._print_final_summary(state)

    def _print_final_summary(self, state: ResearchState):
        table = Table(title="Execution Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Total Cycles", str(state.iterations))
        table.add_row("Unique Sources Found", str(state.urls_found))
        table.add_row("Successful Downloads", str(state.successful_downloads))
        table.add_row("Successful Extractions", str(state.successful_extractions))
        table.add_row("Successful Summaries", str(state.successful_summaries))
        table.add_row("Failed Source Attempts", str(len(state.failed_pages)))
        table.add_row("Final Confidence", f"{state.confidence_score:.2f}")
        console.print(table)
