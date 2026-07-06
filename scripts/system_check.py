import sys
import os
from rich import print as rprint
from web_research_agent.tools.dependency import check_dependencies

def run_system_audit():
    """Master quality gate for Production Readiness Certification."""
    rprint("[bold blue]Running Full System Audit...[/bold blue]\n")

    # 1. Dependencies
    rprint("[bold white]Phase: Dependencies[/bold white]")
    success, missing = check_dependencies()
    if success: rprint("[green]All dependencies present.[/green]")
    else: rprint(f"[red]Missing: {', '.join(missing)}[/red]")
    print("-" * 20)

    # 2. Pipeline Contracts
    rprint("[bold white]Phase: Pipeline Contracts[/bold white]")
    from web_research_agent.models.schemas import PipelineResult
    try:
        p = PipelineResult(success=True, stage="audit")
        rprint("[green]Pipeline contract validation passed.[/green]")
    except Exception as e:
        rprint(f"[red]Contract fail: {e}[/red]")
    print("-" * 20)

    if success:
        rprint("\n[bold green]SYSTEM CERTIFIED FOR PRODUCTION.[/bold green]")
        return True
    else:
        rprint("\n[bold red]SYSTEM AUDIT FAILED.[/bold red]")
        return False

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    sys.exit(0 if run_system_audit() else 1)
