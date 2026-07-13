import importlib
import logging

logger = logging.getLogger(__name__)

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
        "psutil",
        "nest_asyncio"
    ]

    missing = []
    for package in required:
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(package)

    if missing:
        return False, missing
    return True, []
