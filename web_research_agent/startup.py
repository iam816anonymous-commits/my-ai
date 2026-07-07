import os
import sys
import logging
from pathlib import Path
import web_research_agent.config as config

def initialize_directories():
    """Creates every required directory using Path.mkdir(parents=True, exist_ok=True)."""
    required_dirs = [
        config.OUTPUT_DIR,
        config.LOGS_DIR,
        config.CACHE_DIR,
        config.OUTPUT_DIR / "reports",
        config.OUTPUT_DIR / "traces",
        config.OUTPUT_DIR / "exports" / "html",
        config.OUTPUT_DIR / "exports" / "pdf",
        config.OUTPUT_DIR / "exports" / "json",
        config.OUTPUT_DIR / "benchmarks",
        config.OUTPUT_DIR / "runtime"
    ]
    for d in required_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            # Ensure it is writable
            test_file = d / ".keep"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            print(f"CRITICAL ERROR: Could not initialize directory {d}: {e}")

def setup_logging():
    """
    Configures logging with a file fallback mechanism.
    Never crashes due to missing log files.
    """
    log_file = config.LOGS_DIR / "research.log"
    handlers = [logging.StreamHandler()] # Console fallback is always present

    try:
        # Ensure parent exists just in case initialize_directories was skipped
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    except Exception as e:
        print(f"Warning: Could not initialize file logging: {e}. Falling back to console only.")

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True # Override any previous configuration
    )

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized and directories verified.")

    # Module Interface Validation (Regression Protection)
    from web_research_agent.tools.interface_validator import validate_module_interfaces
    if not validate_module_interfaces():
        print("CRITICAL: System Startup Aborted due to Module Interface Drift.")
        sys.exit(1)

def run_health_check():
    """Actionable startup diagnostics."""
    print("\n[bold blue]Autonomous Research Platform - Health Check[/bold blue]")

    # 1. Dependencies
    from web_research_agent.tools.dependency import check_dependencies
    success, missing = check_dependencies()
    if success: print("[green]✓ Dependencies verified.[/green]")
    else:
        print(f"[red]✗ Missing dependencies: {', '.join(missing)}[/red]")
        return False

    # 2. Configuration
    if not config.API_KEY:
        print("[red]✗ API_KEY is missing from environment.[/red]")
        return False
    print("[green]✓ Configuration valid.[/green]")

    # 3. Network/API Connectivity & Authentication
    import requests
    try:
        resp = requests.get(f"{config.BASE_URL}/models", headers={"Authorization": f"Bearer {config.API_KEY}"}, timeout=10)
        if resp.status_code == 401:
            print("[red]✗ Authentication failed (401). Invalid API_KEY.[/red]")
            return False
        elif resp.status_code != 200:
            print(f"[yellow]! LLM Provider check returned status {resp.status_code}.[/yellow]")
        else:
            print("[green]✓ LLM Provider connectivity & Authentication verified.[/green]")
    except Exception as e:
        print(f"[yellow]! LLM Provider check failed: {e}[/yellow]")

    print("[bold green]System Health: READY[/bold green]\n")
    return True
