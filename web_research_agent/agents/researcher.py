import logging
import os
from datetime import datetime
from rich.console import Console
from web_research_agent.config import LOGS_DIR, OUTPUT_DIR
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_html
from web_research_agent.tools.extractor import extract_text
from web_research_agent.tools.summarizer import summarize_article
from web_research_agent.tools.reporter import generate_final_report
from web_research_agent.tools.planner import generate_research_plan
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
        logger.info(f"Starting research for query: {query}")
        console.print(f"[bold blue]Starting research for:[/bold blue] {query}")

        # 1. Planning
        console.print("[yellow]Planning research...[/yellow]")
        state.plan = generate_research_plan(query, self.llm_client)
        logger.info(f"Research Plan: {state.plan}")
        console.print(f"Generated [green]{len(state.plan.queries)}[/green] search queries.")
        console.print(f"Objectives: [cyan]{len(state.plan.objectives)}[/cyan]")

        # 2. Search
        console.print("[yellow]Searching the web...[/yellow]")
        urls = search_web(state.plan.queries, max_results_total=12)
        state.sources_collected = urls
        state.searches_completed = len(state.plan.queries)
        logger.info(f"Found {len(urls)} URLs after filtering and scoring.")
        console.print(f"Found [green]{len(urls)}[/green] high-quality URLs.")

        if not urls:
            console.print("[red]No URLs found for the query.[/red]")
            return

        # 3. Process each URL
        for i, url in enumerate(urls, 1):
            console.print(f"[yellow]Processing ({i}/{len(urls)}):[/yellow] {url}")

            try:
                # Download
                html = fetch_html(url)
                if not html:
                    logger.warning(f"Failed to fetch HTML for {url}")
                    state.failed_pages.append(url)
                    continue
                state.pages_downloaded += 1

                # Extract
                text = extract_text(html)
                if not text:
                    logger.warning(f"Failed to extract text for {url}")
                    state.failed_pages.append(url)
                    continue

                # Summarize
                console.print(f"  [cyan]Summarizing...[/cyan]")
                summary_text = summarize_article(text, self.llm_client)

                state.summaries.append(ArticleSummary(
                    url=url,
                    summary=summary_text
                ))
                state.pages_summarized += 1
                logger.info(f"Successfully processed and summarized {url}")

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                console.print(f"  [red]Error processing {url}[/red]")
                state.failed_pages.append(url)
                continue

        if not state.summaries:
            console.print("[red]Could not generate any summaries. Report aborted.[/red]")
            return

        # 4. Generate Report
        console.print("[yellow]Generating final report...[/yellow]")
        state.report_status = "generating"
        report = generate_final_report(state.summaries, state.plan, self.llm_client)

        # 5. Save Report
        output_file = OUTPUT_DIR / "report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        state.report_status = "completed"
        logger.info(f"Report generated and saved to {output_file}")
        console.print(f"[bold green]Research completed![/bold green] Report saved to {output_file}")

        # Print summary of state
        console.print(f"\n[bold]Research Summary:[/bold]")
        console.print(f"- Pages processed: {state.pages_summarized}")
        console.print(f"- Failed pages: {len(state.failed_pages)}")
        if state.failed_pages:
             logger.info(f"Failed pages list: {state.failed_pages}")
