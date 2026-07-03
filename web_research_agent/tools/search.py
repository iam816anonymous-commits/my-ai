import logging
import re
from typing import List, Dict, Tuple, Any
from ddgs import DDGS
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from web_research_agent.config import MAX_SEARCH_RESULTS, REQUEST_TIMEOUT
from web_research_agent.models.schemas import SourceV2Info

logger = logging.getLogger(__name__)

QUALITY_WEIGHTS = {
    "arxiv.org": (100, "Research Paper"),
    "nature.com": (100, "Research Paper"),
    "science.org": (100, "Research Paper"),
    "ieee.org": (100, "Research Paper"),
    "acm.org": (100, "Research Paper"),
    "microsoft.com": (98, "Official Documentation"),
    "openai.com": (98, "Official Documentation"),
    "anthropic.com": (98, "Official Documentation"),
    "nvidia.com": (98, "Official Documentation"),
    "google.com": (98, "Official Documentation"),
    "docs.": (98, "Official Documentation"),
    ".edu": (96, "University"),
    ".gov": (94, "Government"),
    "reuters.com": (88, "News"),
    "apnews.com": (88, "News"),
    "bbc.com": (88, "News"),
    "github.com": (82, "Technical Documentation"),
    "medium.com": (60, "Blog"),
}

BLACKLIST = {
    "youtube.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "tiktok.com", "quora.com", "reddit.com", "pinterest.com"
}

def get_source_v2_info(url: str, title: str = "") -> SourceV2Info:
    """Enhanced scoring engine V2."""
    url_lower = url.lower()
    netloc = urlparse(url_lower).netloc

    score = 30 # Default
    stype = "General Web"

    # Officiality / Domain Authority
    for domain, (weight, dtype) in QUALITY_WEIGHTS.items():
        if domain.startswith(".") and netloc.endswith(domain):
            score, stype = weight, dtype
            break
        elif domain in netloc:
            score, stype = weight, dtype
            break

    # Technical Depth / Keywords in title
    if any(k in title.lower() for k in ["guide", "documentation", "api", "paper", "research", "architecture"]):
        score += 5

    # Freshness (simulated based on path keywords if no real date)
    if "2024" in url or "2025" in url:
        score += 5

    # Path check for SEO markers
    if any(k in url_lower for k in ["best-", "top-10", "review-"]):
        score -= 15

    return SourceV2Info(url=url, score=float(score), type=stype)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info]]:
    """
    Search with traceability for rejected URLs.
    """
    found_map = {} # url -> info
    rejected = []
    seen_domains = {}

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = ddgs.text(query, max_results=10)
                if not results: continue

                for r in results:
                    url = r.get("href")
                    if not url: continue

                    # Normalization
                    parsed = urlparse(url)
                    norm_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

                    info = get_source_v2_info(norm_url, r.get("title", ""))

                    # Rejection Logic
                    if any(b in parsed.netloc.lower() for b in BLACKLIST):
                        info.rejection_reason = "Blacklisted domain"
                        rejected.append(info)
                        continue

                    if any(ext in norm_url.lower() for ext in [".docx", ".pptx", ".xlsx", ".zip"]):
                        info.rejection_reason = "Unsupported file type"
                        rejected.append(info)
                        continue

                    # Diversity: Max 2 from same domain
                    domain = parsed.netloc.lower()
                    seen_domains[domain] = seen_domains.get(domain, 0) + 1
                    if seen_domains[domain] > 2:
                        info.rejection_reason = "Source diversity limit reached for domain"
                        rejected.append(info)
                        continue

                    if norm_url not in found_map:
                        found_map[norm_url] = {
                            "url": norm_url,
                            "title": r.get("title", ""),
                            "score": info.score,
                            "source_type": info.type
                        }
            except Exception as e:
                logger.warning(f"Search query failed: {query} - {e}")

    sorted_results = sorted(found_map.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results[:max_results_total], rejected
