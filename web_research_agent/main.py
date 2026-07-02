import typer
from web_research_agent.agents.researcher import ResearchAgent
from web_research_agent.config import validate_config
from typing import Optional

app = typer.Typer()

@app.command()
def research(query: str):
    """
    Research a topic and generate a Markdown report.
    """
    validate_config()
    agent = ResearchAgent()
    agent.run(query)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, query: Optional[str] = typer.Argument(None)):
    """
    Support running with command or directly with argument.
    """
    if ctx.invoked_subcommand is None:
        if query:
            validate_config()
            agent = ResearchAgent()
            agent.run(query)
        else:
            print(ctx.get_help())

if __name__ == "__main__":
    app()
