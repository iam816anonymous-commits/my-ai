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
from web_research_agent.models.llm import LLMClient

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
        logger.info(f"Starting research for query: {query}")
        console.print(f"[bold blue]Starting research for:[/bold blue] {query}")

        # 1. Search
        console.print("[yellow]Searching the web...[/yellow]")
        urls = search_web(query)
        logger.info(f"Found URLs: {urls}")

        if not urls:
            console.print("[red]No URLs found for the query.[/red]")
            return

        summaries = []

        # 2. Process each URL
        for i, url in enumerate(urls, 1):
            console.print(f"[yellow]Processing ({i}/{len(urls)}):[/yellow] {url}")

            try:
                # Download
                html = fetch_html(url)
                if not html:
                    logger.warning(f"Failed to fetch HTML for {url}")
                    continue

                # Extract
                text = extract_text(html)
                if not text:
                    logger.warning(f"Failed to extract text for {url}")
                    continue

                # Summarize
                console.print(f"  [cyan]Summarizing...[/cyan]")
                summary = summarize_article(text, self.llm_client)

                summaries.append({
                    "url": url,
                    "summary": summary
                })
                logger.info(f"Successfully processed and summarized {url}")

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                console.print(f"  [red]Error processing {url}[/red]")
                continue

        if not summaries:
            console.print("[red]Could not generate any summaries. Report aborted.[/red]")
            return

        # 3. Generate Report
        console.print("[yellow]Generating final report...[/yellow]")
        report = generate_final_report(summaries, self.llm_client)

        # 4. Save Report
        output_file = OUTPUT_DIR / "report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"Report generated and saved to {output_file}")
        console.print(f"[bold green]Research completed![/bold green] Report saved to {output_file}")
