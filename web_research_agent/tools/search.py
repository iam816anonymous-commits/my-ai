import logging
from typing import List, Dict
from duckduckgo_search import DDGS
from web_research_agent.config import MAX_RESULTS
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    """
    Normalizes a URL by removing fragments and trailing slashes.
    """
    parsed = urlparse(url)
    # Remove fragments
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

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

    # Low quality / Spam / Social media
    low_quality = [
        "youtube.com", "youtu.be", "facebook.com", "instagram.com", "twitter.com", "x.com",
        "tiktok.com", "pinterest.com", "quora.com", "reddit.com"
    ]

    if any(domain in url_lower for domain in high_quality):
        score += 10
    if any(domain in url_lower for domain in technical):
        score += 5
    if any(domain in url_lower for domain in low_quality):
        score -= 20

    return score

def search_web(queries: List[str], max_results_total: int = 12) -> List[str]:
    """
    Searches the web using multiple queries and returns a ranked list of unique URLs.
    """
    all_urls = set()
    scored_urls = []

    try:
        with DDGS() as ddgs:
            for query in queries:
                logger.info(f"Searching for: {query}")
                results = ddgs.text(query, max_results=10) # Fetch some results for each query

                for result in results:
                    url = result.get("href")
                    if not url:
                        continue

                    normalized = normalize_url(url)

                    # Basic filtering
                    if any(ext in normalized.lower() for ext in [".pdf", ".docx", ".pptx", ".xlsx"]):
                        continue

                    if normalized not in all_urls:
                        all_urls.add(normalized)
                        score = score_url(normalized)
                        scored_urls.append({"url": normalized, "score": score})

    except Exception as e:
        logger.error(f"Search failed: {e}")

    # Sort by score descending
    scored_urls.sort(key=lambda x: x["score"], reverse=True)

    # Return top N URLs
    return [item["url"] for item in scored_urls[:max_results_total]]
