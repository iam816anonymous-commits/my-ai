import logging
from typing import List, Dict, Set, Tuple, Any
from ddgs import DDGS
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from web_research_agent.config import MAX_SEARCH_RESULTS

logger = logging.getLogger(__name__)

# Weighted source scoring
# Priority: 100 Research, 98 Official Docs, 96 Uni, 94 Gov, 92 Standards, 90 Tech Co, 88 News, 82 Tech Docs, 75 Eng Blogs, 60 Medium, 45 Personal, 20 SEO
QUALITY_WEIGHTS = {
    "arxiv.org": (100, "Research Paper"),
    "nature.com": (100, "Research Paper"),
    "science.org": (100, "Research Paper"),
    "ieee.org": (100, "Research Paper"),
    "acm.org": (100, "Research Paper"),
    "microsoft.com": (98, "Official Documentation"),
    "apple.com": (98, "Official Documentation"),
    "google.com": (98, "Official Documentation"),
    "openai.com": (98, "Official Documentation"),
    "anthropic.com": (98, "Official Documentation"),
    "nvidia.com": (98, "Official Documentation"),
    "docs.": (98, "Official Documentation"),
    ".edu": (96, "University"),
    "stanford.edu": (96, "University"),
    "mit.edu": (96, "University"),
    "harvard.edu": (96, "University"),
    ".gov": (94, "Government"),
    "w3.org": (92, "Standards Organization"),
    "iso.org": (92, "Standards Organization"),
    "reuters.com": (88, "News"),
    "apnews.com": (88, "News"),
    "bbc.com": (88, "News"),
    "bloomberg.com": (88, "News"),
    "techcrunch.com": (85, "News"),
    "wired.com": (85, "News"),
    "github.com": (82, "Technical Documentation"),
    "developer.": (82, "Technical Documentation"),
    "medium.com": (60, "Blog"),
    "substack.com": (60, "Blog"),
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

def get_source_info(url: str) -> Tuple[int, str]:
    """Categorizes URL and returns score and type."""
    url_lower = url.lower()
    netloc = urlparse(url_lower).netloc

    score = 20
    source_type = "Unknown/SEO"

    for domain, (weight, stype) in QUALITY_WEIGHTS.items():
        if domain.startswith(".") and netloc.endswith(domain):
            if weight > score:
                score, source_type = weight, stype
        elif domain in netloc:
            if weight > score:
                score, source_type = weight, stype

    if "arxiv.org/abs/" in url_lower:
        score += 2

    return score, source_type

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> List[Dict[str, Any]]:
    """
    Searches using multiple queries. Returns a list of dicts with url and quality info.
    """
    all_urls = set()
    scored_urls = []
    seen_domains = set()

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
                    if any(ext in normalized.lower() for ext in [".docx", ".pptx", ".xlsx", ".zip", ".gz"]):
                        continue

                    if normalized not in all_urls:
                        all_urls.add(normalized)
                        score, source_type = get_source_info(normalized)

                        if netloc in seen_domains:
                            score -= 15
                        seen_domains.add(netloc)

                        scored_urls.append({
                            "url": normalized,
                            "score": score,
                            "source_type": source_type
                        })
            except Exception as e:
                logger.warning(f"Search failed for '{query}': {e}")
                continue

    scored_urls.sort(key=lambda x: x["score"], reverse=True)
    return scored_urls[:max_results_total]
