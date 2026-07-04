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

# Authoritative Tiers V5
TIER_1 = {"arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org", "mit.edu", "stanford.edu", "harvard.edu", ".gov", "w3.org", "iso.org"}
TIER_2 = {"microsoft.com", "google.com", "openai.com", "anthropic.com", "nvidia.com", "github.com", "docs.", "developer.", "gartner.com", "mckinsey.com"}
TIER_3 = {"reuters.com", "apnews.com", "bbc.com", "bloomberg.com", "techcrunch.com", "wired.com"}

def get_source_v5_info(url: str, title: str = "") -> SourceV2Info:
    url_lower = url.lower()
    netloc = urlparse(url_lower).netloc

    score = float(WEIGHT_TIER_5)
    tier = 5
    stype = "Web"

    if any(d in url_lower for d in TIER_1):
        score, tier, stype = float(WEIGHT_TIER_1), 1, "Academic/Institutional"
    elif any(d in url_lower for d in TIER_2):
        score, tier, stype = float(WEIGHT_TIER_2), 2, "Technical/Official"
    elif any(d in url_lower for d in TIER_3):
        score, tier, stype = float(WEIGHT_TIER_3), 3, "Media"
    elif any(d in url_lower for d in ["blog.", "engineering.", "substack.com"]):
        score, tier, stype = float(WEIGHT_TIER_4), 4, "Technical Blog"

    # Validation
    rej = None
    if any(p in url_lower for p in ["/search?", "/login", "/signup", "cookie-policy", "captcha"]):
        rej = "Non-research page"
    elif len(url_lower) < 15:
        rej = "Thin URL"

    # Freshness
    if str(time.localtime().tm_year) in url or str(time.localtime().tm_year) in title:
        score += 10

    return SourceV2Info(url=url, score=score, tier=tier, type=stype, rejection_reason=rej)

class SearchEngineManager:
    def __init__(self):
        self.health = {"duckduckgo": SearchHealth()}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    def search(self, queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
        found = {}
        rejected = []
        seen_fingerprints = set()

        provider = "duckduckgo"
        start = time.time()

        try:
            with DDGS() as ddgs:
                for q in queries:
                    try:
                        results = ddgs.text(q, max_results=15)
                        if not results: continue
                        for r in results:
                            url = r.get("href")
                            if not url: continue

                            info = get_source_v5_info(url, r.get("title", ""))
                            if info.rejection_reason:
                                rejected.append(info)
                                continue

                            # Duplicate Intelligence
                            p = urlparse(url)
                            fp = f"{p.netloc}{p.path}".rstrip("/")
                            if fp in seen_fingerprints:
                                info.rejection_reason = "Duplicate mirror"
                                rejected.append(info)
                                continue
                            seen_fingerprints.add(fp)

                            if url not in found:
                                found[url] = {"url": url, "title": r.get("title", ""), "score": info.score, "tier": info.tier, "source_type": info.type}
                    except:
                        self.health[provider].timeouts += 1

            self.health[provider].avg_latency = (time.time() - start) / max(len(queries), 1)
        except Exception as e:
            logger.error(f"Search Manager fatal: {e}")
            self.health[provider].success_rate = 0.0

        sorted_res = sorted(found.values(), key=lambda x: x["score"], reverse=True)
        return sorted_res[:max_results_total], rejected, self.health

def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
    return SearchEngineManager().search(queries, max_results_total)
