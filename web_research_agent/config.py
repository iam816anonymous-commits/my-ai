import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

def get_env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None: return default
    return val.lower() in ("true", "1", "yes", "on")

def get_env_int(key: str, default: int) -> int:
    try: return int(os.getenv(key, str(default)))
    except (ValueError, TypeError): return default

# ==================================================
# LLM Configuration
# ==================================================
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")

# ==================================================
# Research Configuration
# ==================================================
MAX_ITERATIONS = get_env_int("MAX_ITERATIONS", 3)
MAX_SEARCH_RESULTS = get_env_int("MAX_SEARCH_RESULTS", 5)
MAX_ARTICLE_CHARS = get_env_int("MAX_ARTICLE_CHARS", 4000)
MAX_SUMMARY_WORDS = get_env_int("MAX_SUMMARY_WORDS", 250)
MAX_RETRIES = get_env_int("MAX_RETRIES", 3)
REQUEST_TIMEOUT = get_env_int("REQUEST_TIMEOUT", 30)
CONCURRENCY = get_env_int("CONCURRENCY", 5)
CONFIDENCE_THRESHOLD = get_env_int("CONFIDENCE_THRESHOLD", 90)
EVIDENCE_SATURATION_THRESHOLD = get_env_int("EVIDENCE_SATURATION_THRESHOLD", 3)

# Source Weights
WEIGHT_TIER_1 = get_env_int("WEIGHT_TIER_1", 100)
WEIGHT_TIER_2 = get_env_int("WEIGHT_TIER_2", 85)
WEIGHT_TIER_3 = get_env_int("WEIGHT_TIER_3", 70)
WEIGHT_TIER_4 = get_env_int("WEIGHT_TIER_4", 50)
WEIGHT_TIER_5 = get_env_int("WEIGHT_TIER_5", 30)

# ==================================================
# Traceability & Exports
# ==================================================
TRACE_MODE = get_env_bool("TRACE_MODE", True)
EXPORT_FORMATS = os.getenv("EXPORT_FORMATS", "markdown,json,html").split(",")

# ==================================================
# Logging & Debug
# ==================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG = get_env_bool("DEBUG", False)

# ==================================================
# Headers
# ==================================================
HTTP_REFERER = os.getenv("HTTP_REFERER", "")
X_TITLE = os.getenv("X_TITLE", "Web Research Agent")

# ==================================================
# Paths
# ==================================================
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
CACHE_DIR = BASE_DIR / "cache"

OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

def validate_config():
    from rich import print as rprint
    import requests

    # 1. Python Version
    if sys.version_info < (3, 10):
        rprint("[bold red]ERROR: Python 3.10+ required.[/bold red]")
        sys.exit(1)

    # 2. Dependencies
    try:
        from scripts.check_dependencies import check_dependencies
        if not check_dependencies():
            sys.exit(1)
    except ImportError:
        pass

    # 3. API Key
    if not API_KEY:
        rprint("\n[bold red]ERROR: API_KEY is missing![/bold red]")
        rprint("Please set your API_KEY in the .env file.\n")
        sys.exit(1)

    # 4. Network Connectivity (Optional check)
    try:
        requests.get("https://google.com", timeout=5)
    except:
        rprint("[yellow]Warning: No internet connection detected. Pipeline may fail.[/yellow]")

    rprint("[green]Configuration Validated.[/green]")
