import typer
import sys
from web_research_agent.agents.researcher import ResearchAgent
from web_research_agent.config import validate_config
from web_research_agent.startup import initialize_directories, setup_logging
from web_research_agent.tools.storage import storage
from typing import Optional
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

def startup():
    """Centralized startup sequence."""
    initialize_directories()
    setup_logging()
    validate_config()

@app.command()
def health():
    """
    Run system health check.
    """
    from web_research_agent.startup import run_health_check
    if not run_health_check():
        sys.exit(1)

@app.command()
def research(query: str):
    """
    Research a topic and generate an analyst-grade report.
    """
    startup()
    agent = ResearchAgent()
    agent.run(query)

@app.command()
def history():
    """
    Show history of research reports.
    """
    h = storage.get_history()
    if not h:
        console.print("[yellow]No research history found.[/yellow]")
        return

    table = Table(title="Research History")
    table.add_column("ID", style="magenta")
    table.add_column("Query", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Grade", style="bold yellow")
    table.add_column("Conf", style="green")

    for entry in reversed(h):
        table.add_row(
            entry["id"],
            entry["query"][:40],
            entry["created_at"][:10],
            entry["grade"],
            f"{entry['confidence']:.1f}"
        )
    console.print(table)

@app.command()
def open_report(report_id: str):
    """
    Open a previous research report.
    """
    path = storage.get_report_path(report_id)
    if not path:
        console.print(f"[red]Report ID {report_id} not found.[/red]")
        return

    with open(path, "r") as f:
        console.print(f.read())

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, query: Optional[str] = typer.Argument(None)):
    """
    Production Research Platform CLI.
    """
    if ctx.invoked_subcommand is None:
        if query:
            startup()
            agent = ResearchAgent()
            agent.run(query)
        else:
            console.print(ctx.get_help())

if __name__ == "__main__":
    app()
