import os
import sys
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

OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

def validate_config():
    from rich import print as rprint
    if not API_KEY:
        rprint("\n[bold red]ERROR: API_KEY is missing![/bold red]")
        rprint("Please set your API_KEY in the .env file.\n")
        sys.exit(1)
