import logging
from typing import List, Dict
from ddgs import DDGS
from web_research_agent.config import MAX_RESULTS
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Blacklisted domains
BLACKLIST = {
    "news.google.com",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "pinterest.com",
    "youtu.be",
    "instagram.com",
    "x.com",
    "tiktok.com"
}

def normalize_url(url: str) -> str:
    """
    Normalizes a URL by removing fragments and trailing slashes.
    """
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    except Exception as e:
        logger.warning(f"Failed to normalize URL {url}: {e}")
        return url

def score_url(url: str) -> int:
    """
    Scores a URL based on its domain. Higher is better.
    """
    url_lower = url.lower()
    score = 0

    # Official / High-quality domains
    high_quality = [
        ".edu", ".gov", ".org",
        "microsoft.com", "google.com", "openai.com", "anthropic.com", "nvidia.com", "ibm.com",
        "arxiv.org", "nature.com", "science.org",
        "reuters.com", "apnews.com", "bloomberg.com", "technologyreview.com", "wired.com"
    ]

    # Technical / Documentation
    technical = [
        "docs.", "developer.", "github.com", "medium.com", "substack.com", "towardsdatascience.com"
    ]

    if any(domain in url_lower for domain in high_quality):
        score += 10
    if any(domain in url_lower for domain in technical):
        score += 5

    return score

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _execute_search(ddgs: DDGS, query: str) -> List[Dict]:
    """
    Executes a single search query with retries.
    """
    try:
        results = ddgs.text(query, max_results=15)
        return list(results) if results else []
    except Exception as e:
        logger.error(f"Search attempt failed for query '{query}': {str(e)}")
        raise e

def search_web(queries: List[str], max_results_total: int = 12) -> List[str]:
    """
    Searches the web using multiple queries and returns a ranked list of unique URLs.
    Includes blacklisting and normalization.
    """
    all_urls = set()
    scored_urls = []

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = _execute_search(ddgs, query)

                for result in results:
                    url = result.get("href")
                    if not url:
                        continue

                    parsed_url = urlparse(url)
                    if parsed_url.netloc.lower() in BLACKLIST or any(b in parsed_url.netloc.lower() for b in BLACKLIST):
                        logger.debug(f"Skipping blacklisted URL: {url}")
                        continue

                    normalized = normalize_url(url)

                    # Filtering file types
                    if any(ext in normalized.lower() for ext in [".pdf", ".docx", ".pptx", ".xlsx", ".zip", ".gz"]):
                        continue

                    if normalized not in all_urls:
                        all_urls.add(normalized)
                        score = score_url(normalized)
                        scored_urls.append({"url": normalized, "score": score})

            except Exception as e:
                logger.error(f"Persistent failure searching for query '{query}' after retries: {str(e)}")
                continue # Move to next query

    # Sort by score descending
    scored_urls.sort(key=lambda x: x["score"], reverse=True)

    return [item["url"] for item in scored_urls[:max_results_total]]
