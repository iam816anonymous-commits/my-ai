import logging
from typing import List, Dict, Set
from ddgs import DDGS
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from web_research_agent.config import MAX_SEARCH_RESULTS

logger = logging.getLogger(__name__)

# Weighted source scoring
# Priority: 100 Research, 98 Official Docs, 96 Uni, 94 Gov, 92 Standards, 90 Tech Co, 88 News, 82 Tech Docs, 75 Eng Blogs, 60 Medium, 45 Personal, 20 SEO
QUALITY_WEIGHTS = {
    "arxiv.org": 100,
    "nature.com": 100,
    "science.org": 100,
    "ieee.org": 100,
    "acm.org": 100,
    "microsoft.com": 98,
    "apple.com": 98,
    "google.com": 98,
    "openai.com": 98,
    "anthropic.com": 98,
    "nvidia.com": 98,
    "docs.": 98,
    ".edu": 96,
    "stanford.edu": 96,
    "mit.edu": 96,
    "harvard.edu": 96,
    ".gov": 94,
    "w3.org": 92,
    "iso.org": 92,
    "reuters.com": 88,
    "apnews.com": 88,
    "bbc.com": 88,
    "bloomberg.com": 88,
    "techcrunch.com": 85,
    "wired.com": 85,
    "github.com": 82,
    "developer.": 82,
    "medium.com": 60,
    "substack.com": 60,
}

BLACKLIST = {
    "news.google.com", "youtube.com", "facebook.com", "twitter.com", "pinterest.com",
    "youtu.be", "instagram.com", "x.com", "tiktok.com", "quora.com", "reddit.com"
}

def normalize_url(url: str) -> str:
    """Normalizes a URL by removing fragments and trailing slashes."""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    except:
        return url

def score_url(url: str) -> int:
    """Scores a URL based on its domain and path."""
    url_lower = url.lower()
    netloc = urlparse(url_lower).netloc

    # Start with base score
    score = 20 # Default for unknown

    # Check exact match or suffix for quality weights
    for domain, weight in QUALITY_WEIGHTS.items():
        if domain.startswith(".") and netloc.endswith(domain):
            score = max(score, weight)
        elif domain in netloc:
            score = max(score, weight)

    # Arxiv preference
    if "arxiv.org/abs/" in url_lower:
        score += 2 # Prefer landing page over direct PDF

    return score

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> List[str]:
    """
    Searches using multiple queries. Optimized for high-quality and diverse pages.
    """
    all_urls = set()
    scored_urls = []
    seen_domains = set() # For diversity

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = ddgs.text(query, max_results=10)
                for result in results:
                    url = result.get("href")
                    if not url: continue

                    netloc = urlparse(url).netloc.lower()
                    if any(b in netloc for b in BLACKLIST): continue

                    normalized = normalize_url(url)

                    # Filtering file types except ArXiv (which we'll handle in extractor)
                    if any(ext in normalized.lower() for ext in [".docx", ".pptx", ".xlsx", ".zip", ".gz"]):
                        continue

                    if normalized not in all_urls:
                        all_urls.add(normalized)
                        score = score_url(normalized)

                        # Diversity bonus: penalize repeat domains slightly to favor new perspectives
                        if netloc in seen_domains:
                            score -= 15
                        seen_domains.add(netloc)

                        scored_urls.append({"url": normalized, "score": score})
            except Exception as e:
                logger.warning(f"Search failed for '{query}': {e}")
                continue

    # Sort by score descending
    scored_urls.sort(key=lambda x: x["score"], reverse=True)

    # Return top N URLs
    return [item["url"] for item in scored_urls[:max_results_total]]
