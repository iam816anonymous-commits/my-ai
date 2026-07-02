import logging
from typing import List, Dict
from ddgs import DDGS
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
    """Normalizes a URL."""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    except:
        return url

def score_url(url: str) -> int:
    """Scores a URL based on its domain."""
    url_lower = url.lower()
    score = 0
    if any(domain in url_lower for domain in [".edu", ".gov", ".org", "openai.com", "arxiv.org"]):
        score += 10
    if any(domain in url_lower for domain in ["docs.", "developer.", "github.com"]):
        score += 5
    return score

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
def search_web(queries: List[str], max_results_total: int = 5) -> List[str]:
    """
    Searches using multiple queries. Optimized for 5 high-quality pages.
    """
    all_urls = set()
    scored_urls = []

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = ddgs.text(query, max_results=5)
                for result in results:
                    url = result.get("href")
                    if not url: continue

                    netloc = urlparse(url).netloc.lower()
                    if any(b in netloc for b in BLACKLIST): continue

                    normalized = normalize_url(url)
                    if normalized not in all_urls:
                        all_urls.add(normalized)
                        scored_urls.append({"url": normalized, "score": score_url(normalized)})
            except Exception as e:
                logger.warning(f"Search for '{query}' failed: {e}")
                continue

    scored_urls.sort(key=lambda x: x["score"], reverse=True)
    return [item["url"] for item in scored_urls[:max_results_total]]
