import sys
import os
from rich import print as rprint
from web_research_agent.tools.dependency import check_dependencies
from scripts.filesystem_check import check_filesystem
from scripts.pipeline_check import check_pipeline_contracts
from scripts.health_check import check_health

def run_system_audit():
    """Master quality gate for Production Readiness Certification."""
    rprint("[bold blue]Running Full System Audit...[/bold blue]\n")

    checks = [
        ("Dependencies", check_dependencies),
        ("Filesystem", check_filesystem),
        ("Pipeline Contracts", check_pipeline_contracts),
        ("Provider Health", check_health)
    ]

    results = []
    for name, func in checks:
        rprint(f"[bold white]Phase: {name}[/bold white]")
        if name == "Dependencies":
            success, missing = func()
            if success: rprint("[green]All dependencies present.[/green]")
            else: rprint(f"[red]Missing: {', '.join(missing)}[/red]")
        else:
            success = func()
        results.append((name, success))
        print("-" * 20)

    all_pass = all(s for _, s in results)

    rprint("\n[bold]System Audit Summary:[/bold]")
    for name, success in results:
        status = "[green]Pass[/green]" if success else "[red]Fail[/red]"
        rprint(f"- {name}: {status}")

    if all_pass:
        rprint("\n[bold green]SYSTEM CERTIFIED FOR PRODUCTION.[/bold green]")
        return True
    else:
        rprint("\n[bold red]SYSTEM AUDIT FAILED.[/bold red]")
        return False

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    sys.exit(0 if run_system_audit() else 1)
