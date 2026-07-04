import os
import logging
from pathlib import Path
from web_research_agent.config import OUTPUT_DIR, LOGS_DIR, CACHE_DIR, LOG_LEVEL

def initialize_directories():
    """Creates every required directory using Path.mkdir(parents=True, exist_ok=True)."""
    required_dirs = [
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
    for d in required_dirs:
        d.mkdir(parents=True, exist_ok=True)

def setup_logging():
    """
    Configures logging with a file fallback mechanism.
    Never crashes due to missing log files.
    """
    log_file = LOGS_DIR / "research.log"
    handlers = [logging.StreamHandler()] # Console fallback is always present

    try:
        # Ensure parent exists just in case initialize_directories was skipped
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    except Exception as e:
        print(f"Warning: Could not initialize file logging: {e}. Falling back to console only.")

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True # Override any previous configuration
    )
