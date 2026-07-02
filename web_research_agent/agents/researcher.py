import logging
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from web_research_agent.config import LOGS_DIR, OUTPUT_DIR
from web_research_agent.tools.search import search_web
from web_research_agent.tools.browser import fetch_html
from web_research_agent.tools.extractor import extract_text
from web_research_agent.tools.summarizer import summarize_article
from web_research_agent.tools.reporter import generate_final_report
from web_research_agent.tools.planner import generate_research_plan, get_fallback_plan
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
        try:
            state.plan = generate_research_plan(query, self.llm_client)
        except Exception as e:
            logger.error(f"Intelligent planning failed after retries: {str(e)}. Using fallback plan.")
            state.plan = get_fallback_plan(query)

        logger.info(f"Research Plan: {state.plan}")
        console.print(f"Generated [green]{len(state.plan.queries)}[/green] search queries.")
        console.print(f"Objectives: [cyan]{len(state.plan.objectives)}[/cyan]")

        # 2. Search
        console.print("[yellow]Searching the web...[/yellow]")
        urls = search_web(state.plan.queries, max_results_total=12)
        state.sources_collected = urls
        state.urls_found = len(urls)
        logger.info(f"Found {len(urls)} unique URLs after filtering and scoring.")
        console.print(f"Found [green]{len(urls)}[/green] high-quality URLs.")

        if not urls:
            console.print("[red]No URLs found for the query. Research aborted.[/red]")
            return

        # 3. Process each URL
        for i, url in enumerate(urls, 1):
            state.urls_processed += 1
            console.print(f"[yellow]Processing ({i}/{len(urls)}):[/yellow] {url}")

            try:
                # Download
                html = fetch_html(url)
                if not html:
                    reason = "Failed to download HTML (empty or error)"
                    logger.warning(f"{reason}: {url}")
                    state.failed_pages.append({"url": url, "reason": reason})
                    continue
                state.successful_downloads += 1

                # Extract
                text = extract_text(html)
                if not text:
                    reason = "Failed to extract meaningful text"
                    logger.warning(f"{reason}: {url}")
                    state.failed_pages.append({"url": url, "reason": reason})
                    continue
                state.successful_extractions += 1

                # Summarize
                console.print(f"  [cyan]Summarizing...[/cyan]")
                summary_text = summarize_article(text, self.llm_client)
                if not summary_text or "failed" in summary_text.lower():
                     reason = "Summarization failed"
                     logger.warning(f"{reason}: {url}")
                     state.failed_pages.append({"url": url, "reason": reason})
                     continue

                state.summaries.append(ArticleSummary(
                    url=url,
                    summary=summary_text
                ))
                state.successful_summaries += 1
                logger.info(f"Successfully processed and summarized {url}")

            except Exception as e:
                reason = f"Unexpected error: {str(e)}"
                logger.error(f"{reason} while processing {url}")
                console.print(f"  [red]Error processing {url}[/red]")
                state.failed_pages.append({"url": url, "reason": reason})
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
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
            state.report_status = "completed"
            logger.info(f"Report generated and saved to {output_file}")
            console.print(f"[bold green]Research completed![/bold green] Report saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save report to {output_file}: {e}")
            console.print(f"[red]Failed to save report.[/red]")
            state.report_status = "failed_to_save"

        # 6. Runtime Statistics
        self._display_statistics(state)

    def _display_statistics(self, state: ResearchState):
        """
        Displays accurate runtime statistics in a formatted table.
        """
        table = Table(title="Research Runtime Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("URLs Found", str(state.urls_found))
        table.add_row("URLs Processed", str(state.urls_processed))
        table.add_row("Successful Downloads", str(state.successful_downloads))
        table.add_row("Successful Extractions", str(state.successful_extractions))
        table.add_row("Successful Summaries", str(state.successful_summaries))
        table.add_row("Failed Pages", str(len(state.failed_pages)))

        # Basic confidence calculation
        if state.urls_found > 0:
            confidence = (state.successful_summaries / state.urls_found) * 1.0
            state.confidence_score = round(min(confidence, 1.0), 2)
        else:
            state.confidence_score = 0.0

        table.add_row("Final Confidence", str(state.confidence_score))

        console.print("\n")
        console.print(table)

        if state.failed_pages:
             logger.info("Detailed Failure Reasons:")
             for failure in state.failed_pages:
                  logger.info(f"- {failure['url']}: {failure['reason']}")
