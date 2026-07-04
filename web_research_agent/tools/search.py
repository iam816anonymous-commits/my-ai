import logging
import re
import time
from typing import List, Dict, Tuple, Any
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

# Tier 2 (Technical & Corporate Official)
TIER_2_DOMAINS = {
    "microsoft.com", "apple.com", "google.com", "openai.com", "anthropic.com",
    "nvidia.com", "aws.amazon.com", "github.com", "developer.", "docs.",
    "gartner.com", "forrester.com", "mckinsey.com", "hbr.org"
}

# Tier 3 (Established Media)
TIER_3_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bloomberg.com",
    "techcrunch.com", "wired.com", "theverge.com", "technologyreview.com"
}

# Tier 4 (Engineering Blogs)
TIER_4_DOMAINS = {
    "engineering.", "blog.", "netflixtechblog.com", "slack.engineering",
    "substack.com", "towardsdatascience.com", "medium.com/engineering"
}

def get_source_v4_info(url: str, title: str = "") -> SourceV2Info:
    """Quality scoring engine V4: tiering + technical depth + freshness."""
    url_lower = url.lower()
    netloc = urlparse(url_lower).netloc

    score = float(WEIGHT_TIER_5)
    tier = 5
    stype = "General Web"

    # Tier classification
    if any(d in url_lower for d in TIER_1_DOMAINS):
        score, tier, stype = float(WEIGHT_TIER_1), 1, "Academic/Research"
    elif any(d in url_lower for d in TIER_2_DOMAINS):
        score, tier, stype = float(WEIGHT_TIER_2), 2, "Official/Corporate"
    elif any(d in url_lower for d in TIER_3_DOMAINS):
        score, tier, stype = float(WEIGHT_TIER_3), 3, "Press/Media"
    elif any(d in url_lower for d in TIER_4_DOMAINS):
        score, tier, stype = float(WEIGHT_TIER_4), 4, "Technical Blog"

    # Specific Bonuses
    if "/research/" in url_lower or "paper" in title.lower():
        score += 10 # Research paper bonus
    if "docs." in netloc or "developer." in netloc:
        score += 8 # Official documentation bonus
    if any(k in title.lower() for k in ["whitepaper", "report", "analysis"]):
        score += 5 # Industry report bonus

    # Freshness heuristic (URL/title containing recent years)
    current_year = time.localtime().tm_year
    if str(current_year) in url or str(current_year) in title:
        score += 5
    elif str(current_year - 1) in url or str(current_year - 1) in title:
        score += 2

    # SEO/Spam penalties
    if any(k in title.lower() for k in ["top 10", "best of", "buy now", "review"]):
        score -= 20

    return SourceV2Info(url=url, score=score, tier=tier, type=stype)

class SearchEngineManager:
    def __init__(self):
        self.health = {"duckduckgo": SearchHealth()}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    def search(self, queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
        found_map = {}
        rejected = []
        seen_domains = {}

        start_time = time.time()
        provider = "duckduckgo"

        try:
            with DDGS() as ddgs:
                for query in queries:
                    try:
                        results = ddgs.text(query, max_results=15)
                        if not results: continue

                        for r in results:
                            url = r.get("href")
                            if not url: continue

                            parsed = urlparse(url)
                            norm_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

                            info = get_source_v4_info(norm_url, r.get("title", ""))

                            # Rejection logic
                            if any(b in parsed.netloc.lower() for b in ["youtube.com", "facebook.com", "twitter.com", "reddit.com", "instagram.com"]):
                                info.rejection_reason = "Blacklisted"
                                rejected.append(info)
                                continue

                            # Diversity logic
                            domain = parsed.netloc.lower()
                            seen_domains[domain] = seen_domains.get(domain, 0) + 1
                            if seen_domains[domain] > 2:
                                info.rejection_reason = "Diversity Limit"
                                rejected.append(info)
                                continue

                            if norm_url not in found_map:
                                found_map[norm_url] = {
                                    "url": norm_url,
                                    "title": r.get("title", ""),
                                    "score": info.score,
                                    "tier": info.tier,
                                    "source_type": info.type
                                }
                    except Exception as e:
                        logger.warning(f"Query '{query}' failed: {e}")
                        self.health[provider].timeouts += 1

            self.health[provider].avg_latency = (time.time() - start_time) / len(queries)
            self.health[provider].success_rate = 1.0
        except Exception as e:
            logger.error(f"Search fatal: {e}")
            self.health[provider].success_rate = 0.0

        sorted_results = sorted(found_map.values(), key=lambda x: x["score"], reverse=True)
        return sorted_results[:max_results_total], rejected, self.health

def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
    manager = SearchEngineManager()
    return manager.search(queries, max_results_total)
