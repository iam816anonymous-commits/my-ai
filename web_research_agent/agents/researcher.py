import logging
from rich.console import Console
from rich.table import Table
from web_research_agent.config import LOGS_DIR, OUTPUT_DIR
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_html
from web_research_agent.tools.extractor import extract_text
from web_research_agent.tools.summarizer import summarize_article, generate_fallback_summary
from web_research_agent.tools.reporter import generate_final_report
from web_research_agent.tools.planner import generate_research_plan
from web_research_agent.tools.reasoner import evaluate_research, update_knowledge_base
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchState, ArticleSummary, KnowledgeBaseEntry

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
        console.print(f"[bold blue]Starting research:[/bold blue] {query}")

        # 1. Planning
        console.print("[yellow]Planning...[/yellow]")
        state.plan = generate_research_plan(query, self.llm_client)

        # 2. Research Loop
        max_iterations = 3
        while state.iterations < max_iterations:
            state.iterations += 1
            console.print(f"\n[bold green]Iteration {state.iterations}/{max_iterations}[/bold green]")

            # Determine queries: plan queries in iter 1, follow-up queries in later iters
            current_queries = state.plan.queries if state.iterations == 1 else state.follow_up_queries
            if not current_queries:
                break

            # Search
            console.print(f"Searching...")
            urls = search_web(current_queries, max_results_total=5)
            # Filter URLs we already have
            new_urls = [u for u in urls if u not in state.sources_collected]
            state.sources_collected.extend(new_urls)
            state.urls_found += len(new_urls)

            # Process URLs
            iteration_summaries = []
            for url in new_urls:
                console.print(f"Processing: {url}")
                try:
                    html = fetch_html(url)
                    if not html: raise ValueError("No HTML")
                    state.successful_downloads += 1

                    text = extract_text(html)
                    if not text: raise ValueError("No Text")
                    state.successful_extractions += 1

                    summary = summarize_article(text, self.llm_client)
                    article_summary = ArticleSummary(url=url, summary=summary)
                    iteration_summaries.append(article_summary)
                    state.summaries.append(article_summary)
                    state.successful_summaries += 1
                except Exception as e:
                    logger.warning(f"Failed {url}: {e}")
                    state.failed_pages.append({"url": url, "reason": str(e)})

            # Update Knowledge Base
            state.knowledge_base = update_knowledge_base(state.knowledge_base, iteration_summaries, state.plan)

            # Reasoning
            console.print("[yellow]Reasoning...[/yellow]")
            reasoning = evaluate_research(query, state.plan, state.summaries, self.llm_client)

            state.objective_coverage = reasoning.objective_coverage
            state.contradictions.extend(reasoning.contradictions)
            state.follow_up_queries = reasoning.follow_up_queries
            state.confidence_score = reasoning.confidence / 100.0

            # Stop conditions
            if not reasoning.continue_research:
                console.print("Objectives met. Stopping.")
                break

            if all(cov >= 90 for cov in state.objective_coverage.values()):
                console.print("High coverage reached. Stopping.")
                break

            if not new_urls:
                console.print("No new sources found. Stopping.")
                break

        # 3. Report
        console.print("[yellow]Generating report...[/yellow]")
        report = generate_final_report(
            state.summaries,
            state.plan,
            self.llm_client,
            iterations=state.iterations,
            coverage=state.objective_coverage,
            contradictions=state.contradictions
        )

        # Save
        output_file = OUTPUT_DIR / "report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        console.print(f"[bold green]Done![/bold green] Report: {output_file}")
        self._display_stats(state)

    def _display_stats(self, state: ResearchState):
        table = Table(title="Research Stats")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Iterations", str(state.iterations))
        table.add_row("URLs Found", str(state.urls_found))
        table.add_row("Successful Downloads", str(state.successful_downloads))
        table.add_row("Successful Extractions", str(state.successful_extractions))
        table.add_row("Successful Summaries", str(state.successful_summaries))
        table.add_row("Failed Pages", str(len(state.failed_pages)))
        table.add_row("Final Confidence", f"{state.confidence_score:.2f}")
        console.print(table)
