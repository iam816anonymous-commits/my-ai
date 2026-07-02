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
    """Helper to parse boolean environment variables."""
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")

def get_env_int(key: str, default: int) -> int:
    """Helper to parse integer environment variables."""
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default

# ==================================================
# LLM Configuration
# ==================================================
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    # We allow running without API_KEY for tests if needed,
    # but in a real run, the agent will error out gracefully later or we can check now.
    # The requirement says "A clear error is shown if API_KEY is missing".
    # Let's check it only if we're not in a specific "ignore config" mode.
    pass

BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")

# ==================================================
# Research Configuration
# ==================================================
MAX_ITERATIONS = get_env_int("MAX_ITERATIONS", 3)
MAX_SEARCH_RESULTS = get_env_int("MAX_SEARCH_RESULTS", 5)
MAX_ARTICLE_CHARS = get_env_int("MAX_ARTICLE_CHARS", 4000)
MAX_RETRIES = get_env_int("MAX_RETRIES", 3)
REQUEST_TIMEOUT = get_env_int("REQUEST_TIMEOUT", 30)

# ==================================================
# Logging & Debug
# ==================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG = get_env_bool("DEBUG", False)

# ==================================================
# OpenRouter Specific Headers
# ==================================================
HTTP_REFERER = os.getenv("HTTP_REFERER", "")
X_TITLE = os.getenv("X_TITLE", "Web Research Agent")

# ==================================================
# Paths
# ==================================================
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

def validate_config():
    """Validates core configuration and exits on failure."""
    from rich import print as rprint
    if not API_KEY:
        rprint("\n[bold red]ERROR: API_KEY is missing![/bold red]")
        rprint("Please set your API_KEY in the .env file.")
        print("You can get an OpenRouter key at https://openrouter.ai/keys\n")
        sys.exit(1)

    # Simple validation of numeric ranges
    if MAX_ITERATIONS < 1:
        print("Warning: MAX_ITERATIONS must be at least 1. Using default 3.")

    if MAX_SEARCH_RESULTS < 1:
        print("Warning: MAX_SEARCH_RESULTS must be at least 1. Using default 5.")
