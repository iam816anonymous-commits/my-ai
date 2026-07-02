import logging
from typing import List
from duckduckgo_search import DDGS
from web_research_agent.config import MAX_RESULTS

logger = logging.getLogger(__name__)

def search_web(query: str, max_results: int = MAX_RESULTS) -> List[str]:
    """
    Searches the web using DuckDuckGo and returns a list of unique URLs.
    Filters out PDFs, YouTube, and obvious spam/unwanted domains.
    """
    urls = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results * 3) # Fetch more to allow for filtering

            for result in results:
                url = result.get("href")
                if not url:
                    continue

                # Filtering logic
                if any(ext in url.lower() for ext in [".pdf", ".docx", ".pptx", ".xlsx"]):
                    continue

                if any(domain in url.lower() for domain in ["youtube.com", "youtu.be", "facebook.com", "instagram.com", "twitter.com", "x.com"]):
                    continue

                if url not in urls:
                    urls.append(url)

                if len(urls) >= max_results:
                    break

    except Exception as e:
        logger.error(f"Search failed for query '{query}': {e}")

    return urls
