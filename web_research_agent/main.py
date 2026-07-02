import typer
from web_research_agent.agents.researcher import ResearchAgent

app = typer.Typer()

@app.command()
def research(query: str):
    """
    Research a topic and generate a Markdown report.
    """
    agent = ResearchAgent()
    agent.run(query)

if __name__ == "__main__":
    app()
