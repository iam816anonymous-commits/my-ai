import sys
import os
import subprocess
from rich import print as rprint

def run_regression_tests():
    """Runs a series of core queries to ensure stability."""
    queries = [
        "What is Web3?",
        "AI Coding Agents",
        "Zero Trust Architecture"
    ]

    # Check if API_KEY is dummy
    if os.getenv("API_KEY") == "sk-dummy":
        rprint("[yellow]Skipping live regression tests (API_KEY is dummy).[/yellow]")
        return True

    all_pass = True
    for q in queries:
        rprint(f"\n[bold blue]Running regression: {q}[/bold blue]")
        try:
            # We run via CLI to verify the full interface
            res = subprocess.run(
                ["python3", "web_research_agent/main.py", q],
                capture_output=True,
                text=True,
                timeout=600 # 10 min
            )
            if res.returncode == 0:
                rprint(f"[green]PASS: {q}[/green]")
            else:
                rprint(f"[red]FAIL: {q}[/red]")
                rprint(res.stderr)
                all_pass = False
        except Exception as e:
            rprint(f"[red]EXCEPTION during regression: {e}[/red]")
            all_pass = False

    return all_pass

if __name__ == "__main__":
    sys.exit(0 if run_regression_tests() else 1)
