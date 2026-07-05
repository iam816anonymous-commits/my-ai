import logging
import re
import time
from typing import List, Dict, Tuple, Any, Set
from ddgs import DDGS
from urllib.parse import urlparse, urlunparse
from tenacity import retry, stop_after_attempt, wait_exponential
from web_research_agent.config import (
    MAX_SEARCH_RESULTS, WEIGHT_TIER_1, WEIGHT_TIER_2,
    WEIGHT_TIER_3, WEIGHT_TIER_4, WEIGHT_TIER_5
)
from web_research_agent.models.schemas import SourceV2Info, SearchHealth

logger = logging.getLogger(__name__)

# Authoritative Tiers V6
TIER_1 = {
    "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org", "mit.edu", "stanford.edu", "harvard.edu", ".gov", "w3.org", "iso.org",
    "scholar.google.com", "semanticscholar.org", "ncbi.nlm.nih.gov", "ssrn.com", "sec.gov", "bls.gov"
}
TIER_2 = {
    "microsoft.com", "google.com", "openai.com", "anthropic.com", "nvidia.com", "github.com", "docs.", "developer.", "gartner.com", "mckinsey.com",
    "reuters.com", "apnews.com", "bloomberg.com", "ft.com", "wsj.com", "economist.com"
}
TIER_3 = {
    "bbc.com", "techcrunch.com", "wired.com", "verge.com", "infoworld.com", "zdnet.com", "eweek.com"
}

def canonicalize_url(url: str) -> str:
    """Standardizes URL to prevent duplicates (remove fragments, trailing slashes)."""
    try:
        p = urlparse(url)
        # Remove common tracking params
        query = "&".join([q for q in p.query.split("&") if not any(x in q.lower() for x in ["utm_", "ref", "fbclid"])])
        # Reconstruct without fragment and with cleaned query
        new_url = urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), p.params, query, ""))
        return new_url
    except:
        return url

def get_source_v5_info(url: str, title: str = "") -> SourceV2Info:
    url_lower = url.lower()
    netloc = urlparse(url_lower).netloc

    score = float(WEIGHT_TIER_5)
    tier = 5
    stype = "Web"

    # Authority Priority
    if any(d in netloc for d in TIER_1):
        score, tier, stype = float(WEIGHT_TIER_1), 1, "Academic/Institutional"
    elif any(d in netloc for d in TIER_2):
        score, tier, stype = float(WEIGHT_TIER_2), 2, "Technical/Official"
    elif any(d in netloc for d in TIER_3):
        score, tier, stype = float(WEIGHT_TIER_3), 3, "Media"
    elif any(d in netloc for d in ["blog.", "engineering.", "substack.com", "medium.com"]):
        # Medium is Tier 4 now as requested to reduce priority
        score, tier, stype = float(WEIGHT_TIER_4), 4, "Technical Blog"

    # Validation (expanded junk detection)
    rej = None
    junk_patterns = [
        "/search?", "/login", "/signup", "cookie-policy", "captcha",
        "privacy-policy", "terms-of-service", "unsubscribe", "subscribe",
        "account", "settings", "profile", "cart", "checkout"
    ]
    if any(p in url_lower for p in junk_patterns):
        rej = "Non-research page"
    elif len(url_lower) < 15:
        rej = "Thin URL"
    elif any(x in netloc for x in ["linkedin.com", "facebook.com", "twitter.com", "instagram.com"]):
        rej = "Social Media (Low Research Value)"

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

        # Cascading search strategy: if we have few high-tier results, try adding targeted qualifiers
        tier_augmented_queries = []
        for q in queries:
            tier_augmented_queries.append(q)
            if "research" not in q.lower() and "official" not in q.lower():
                tier_augmented_queries.append(f"{q} site:gov OR site:edu")
                tier_augmented_queries.append(f"{q} whitepaper OR documentation")

        try:
            with DDGS() as ddgs:
                for q in tier_augmented_queries:
                    try:
                        results = ddgs.text(q, max_results=20)
                        if not results: continue
                        for r in results:
                            url = r.get("href")
                            if not url: continue

                            c_url = canonicalize_url(url)
                            info = get_source_v5_info(c_url, r.get("title", ""))
                            if info.rejection_reason:
                                rejected.append(info)
                                continue

                            # Duplicate Intelligence (Fingerprint based on netloc + path)
                            p = urlparse(c_url)
                            fp = f"{p.netloc}{p.path}".lower()
                            if fp in seen_fingerprints:
                                info.rejection_reason = "Duplicate mirror"
                                rejected.append(info)
                                continue
                            seen_fingerprints.add(fp)

                            if c_url not in found:
                                found[c_url] = {"url": c_url, "title": r.get("title", ""), "score": info.score, "tier": info.tier, "source_type": info.type}
                    except:
                        self.health[provider].timeouts += 1

            self.health[provider].avg_latency = (time.time() - start) / max(len(queries), 1)
        except Exception as e:
            logger.error(f"Search Manager fatal: {e}")
            self.health[provider].success_rate = 0.0

        sorted_res = sorted(found.values(), key=lambda x: x["score"], reverse=True)
        return sorted_res[:max_results_total], rejected, self.health

def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
    # TASK 2, 3, 4: Strict validation and debugging (PRE-RETRY)
    if isinstance(queries, str):
        raise ValueError(f"CRITICAL REGRESSION: search_web received a STRING instead of a LIST. Query: '{queries}'")

    if not isinstance(queries, list):
        raise ValueError(f"CRITICAL REGRESSION: search_web received {type(queries)} instead of a LIST.")

    # Ensure all elements are strings
    for i, q in enumerate(queries):
        if not isinstance(q, str):
             raise ValueError(f"CRITICAL REGRESSION: search_web received non-string at index {i}: {type(q)}")

    # Debugging Output
    print(f"\nSearch Queries ({len(queries)})")
    print(f"Query Type: {type(queries)}")
    for i, q in enumerate(queries, 1):
        print(f"{i}. {q} (Length: {len(q)})")

    return SearchEngineManager().search(queries, max_results_total)
