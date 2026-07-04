import sys
import importlib

def check_dependencies():
    required = [
        "aiohttp",
        "bs4",
        "duckduckgo_search",
        "lxml",
        "openai",
        "pydantic",
        "pypdf",
        "dotenv",
        "rich",
        "tenacity",
        "trafilatura",
        "typer",
        "requests",
        "psutil"
    ]

    missing = []
    for package in required:
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(package)

    if missing:
        print("\n[bold red]ERROR: Missing Dependencies![/bold red]")
        print(f"The following packages are required but not installed: {', '.join(missing)}")
        print("\nPlease run: pip install -r web_research_agent/requirements.txt\n")
        return False

    print("[green]All dependencies are present.[/green]")
    return True

if __name__ == "__main__":
    from rich import print
    sys.exit(0 if check_dependencies() else 1)
