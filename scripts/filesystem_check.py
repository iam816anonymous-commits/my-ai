import sys
from pathlib import Path
from rich import print as rprint

def check_filesystem():
    from web_research_agent.config import OUTPUT_DIR, LOGS_DIR, CACHE_DIR

    required = [
        OUTPUT_DIR,
        LOGS_DIR,
        CACHE_DIR,
        OUTPUT_DIR / "reports",
        OUTPUT_DIR / "traces",
        OUTPUT_DIR / "exports" / "html",
        OUTPUT_DIR / "exports" / "pdf",
        OUTPUT_DIR / "exports" / "json",
        OUTPUT_DIR / "benchmarks",
        OUTPUT_DIR / "runtime"
    ]

    missing = []
    for d in required:
        if not d.is_dir():
            missing.append(str(d))

    if missing:
        rprint("[bold red]ERROR: Filesystem check failed![/bold red]")
        for m in missing:
            rprint(f"- Missing directory: {m}")
        return False

    # Check permissions (write)
    try:
        test_file = LOGS_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        rprint(f"[bold red]ERROR: Logs directory not writable: {e}[/bold red]")
        return False

    rprint("[green]Filesystem check passed.[/green]")
    return True

if __name__ == "__main__":
    import os
    sys.path.append(os.getcwd())
    from web_research_agent.startup import initialize_directories
    initialize_directories()
    sys.exit(0 if check_filesystem() else 1)
