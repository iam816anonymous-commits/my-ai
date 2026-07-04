import logging
import re
import time
from typing import List, Dict, Tuple, Any, Set
from duckduckgo_search import DDGS
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from web_research_agent.config import (
    MAX_SEARCH_RESULTS, WEIGHT_TIER_1, WEIGHT_TIER_2,
    WEIGHT_TIER_3, WEIGHT_TIER_4, WEIGHT_TIER_5
)
from web_research_agent.models.schemas import SourceV2Info, SearchHealth

logger = logging.getLogger(__name__)

# Tier 1 (Highest Authority)
TIER_1_DOMAINS = {
    "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org",
    "microsoft.com/research", "openai.com/research", "anthropic.com/research",
    "nvidia.com/en-us/research", "google.com/research", "deepmind.google",
    "w3.org", "iso.org", ".gov", ".edu"
}

TIER_2_DOMAINS = {
    "microsoft.com", "apple.com", "google.com", "openai.com", "anthropic.com",
    "nvidia.com", "aws.amazon.com", "github.com", "developer.", "docs.",
    "gartner.com", "forrester.com", "mckinsey.com", "hbr.org", "bloomberg.com/professional"
}

TIER_3_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bloomberg.com",
    "techcrunch.com", "wired.com", "theverge.com", "technologyreview.com"
}

TIER_4_DOMAINS = {
    "engineering.", "blog.", "netflixtechblog.com", "slack.engineering",
    "substack.com", "towardsdatascience.com"
}

def get_source_v5_info(url: str, title: str = "") -> SourceV2Info:
    """Quality scoring engine V5."""
    url_lower = url.lower()
    netloc = urlparse(url_lower).netloc

    score = float(WEIGHT_TIER_5)
    tier = 5
    stype = "General Web"

    # Tiering
    if any(d in url_lower for d in TIER_1_DOMAINS):
        score, tier, stype = float(WEIGHT_TIER_1), 1, "Academic/Institutional"
    elif any(d in url_lower for d in TIER_2_DOMAINS):
        score, tier, stype = float(WEIGHT_TIER_2), 2, "Technical/Official Corp"
    elif any(d in url_lower for d in TIER_3_DOMAINS):
        score, tier, stype = float(WEIGHT_TIER_3), 3, "Established Media"
    elif any(d in url_lower for d in TIER_4_DOMAINS):
        score, tier, stype = float(WEIGHT_TIER_4), 4, "Engineering Blog"

    # Validation: Reject obviously non-research content
    rejection = None
    if any(p in url_lower for p in ["/search?", "google.com/maps", "/login", "/signup", "cookie-policy", "captcha"]):
        rejection = "Non-research utility page"
    elif len(url_lower) < 15:
        rejection = "URL too short/Thin"

    # Bonuses
    if "/research/" in url_lower or "paper" in title.lower(): score += 12
    if "docs." in netloc or "developer." in netloc: score += 10

    # Freshness
    year = time.localtime().tm_year
    if str(year) in url or str(year) in title: score += 7

    return SourceV2Info(url=url, score=score, tier=tier, type=stype, rejection_reason=rejection)

class SearchEngineManager:
    def __init__(self):
        self.health = {"duckduckgo": SearchHealth()}

    def validate_result(self, url: str) -> bool:
        """Heuristic check before extraction."""
        return not any(x in url.lower() for x in ["/ads/", "/promo/", "/category/", "/tag/"])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    def search(self, queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
        found_map = {}
        rejected = []
        seen_fingerprints = set() # For content mirror detection (url base)

        provider = "duckduckgo"
        start_time = time.time()

        try:
            with DDGS() as ddgs:
                for query in queries:
                    try:
                        results = ddgs.text(query, max_results=15)
                        if not results: continue

                        for r in results:
                            url = r.get("href")
                            if not url: continue

                            info = get_source_v5_info(url, r.get("title", ""))
                            if info.rejection_reason:
                                rejected.append(info)
                                continue

                            # Duplicate Intelligence: treat mirrors as one
                            parsed = urlparse(url)
                            fingerprint = f"{parsed.netloc}{parsed.path}".rstrip("/")
                            if fingerprint in seen_fingerprints:
                                info.rejection_reason = "Duplicate content mirror"
                                rejected.append(info)
                                continue
                            seen_fingerprints.add(fingerprint)

                            if url not in found_map:
                                found_map[url] = {
                                    "url": url,
                                    "title": r.get("title", ""),
                                    "score": info.score,
                                    "tier": info.tier,
                                    "source_type": info.type
                                }
                    except Exception as e:
                        logger.warning(f"Query '{query}' fail: {e}")
                        self.health[provider].timeouts += 1

            self.health[provider].avg_latency = (time.time() - start_time) / max(len(queries), 1)
        except Exception as e:
            logger.error(f"Search Manager fatal: {e}")
            self.health[provider].success_rate = 0.0

        sorted_results = sorted(found_map.values(), key=lambda x: x["score"], reverse=True)
        return sorted_results[:max_results_total], rejected, self.health

def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
    return SearchEngineManager().search(queries, max_results_total)
