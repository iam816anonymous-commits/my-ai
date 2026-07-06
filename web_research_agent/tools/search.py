import asyncio
import logging
import re
import time
from typing import List, Dict, Tuple, Any, Set
from duckduckgo_search import DDGS
from urllib.parse import urlparse, urlunparse
from tenacity import retry, stop_after_attempt, wait_exponential
from concurrent.futures import ThreadPoolExecutor
from web_research_agent.config import (
    MAX_SEARCH_RESULTS, WEIGHT_TIER_1, WEIGHT_TIER_2,
    WEIGHT_TIER_3, WEIGHT_TIER_4, WEIGHT_TIER_5, CONCURRENCY
)
from web_research_agent.models.schemas import SourceV2Info, SearchHealth

logger = logging.getLogger(__name__)

# Authoritative Tiers
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
    """Standardizes URL to prevent duplicates (remove fragments, trailing slashes, common tracking params)."""
    try:
        p = urlparse(url)
        # Remove common tracking params
        query_params = []
        if p.query:
            query_params = [q for q in p.query.split("&") if not any(x in q.lower() for x in ["utm_", "ref", "fbclid", "gclid", "source"])]

        # Reconstruct without fragment and with cleaned query
        new_url = urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), p.params, "&".join(query_params), ""))
        return new_url
    except:
        return url

def get_source_v6_info(url: str, title: str = "") -> SourceV2Info:
    """Harden source scoring with diagnostic rejection reasons."""
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
        score, tier, stype = float(WEIGHT_TIER_4), 4, "Technical Blog"

    # Validation (expanded junk detection)
    rej = None
    if any(x in url_lower for x in [".pdf", ".zip", ".exe", ".gz", ".docx", ".pptx"]):
        rej = "Unsupported file format"
    elif any(p in url_lower for p in ["/login", "/signup", "cookie-policy", "captcha", "privacy-policy", "terms-of-service"]):
        rej = "Administrative/Legal page"
    elif len(url_lower) < 15:
        rej = "URL length too short"
    elif any(x in netloc for x in ["linkedin.com", "facebook.com", "twitter.com", "instagram.com", "pinterest.com"]):
        rej = "Social Media (Low Research Value)"
    elif any(x in netloc for x in ["youtube.com", "vimeo.com", "tiktok.com"]):
        rej = "Video platform (Unsupported content)"

    # Freshness boost
    if str(time.localtime().tm_year) in url or str(time.localtime().tm_year) in title:
        score += 10

    return SourceV2Info(url=url, score=score, tier=tier, type=stype, rejection_reason=rej)

class SearchDiagnostics:
    def __init__(self):
        self.queries_executed = []
        self.raw_urls_extracted = 0
        self.duplicate_removals = 0
        self.blacklist_removals = 0
        self.unsupported_file_removals = 0
        self.quality_score_removals = 0
        self.total_rejections = 0
        self.final_urls_retained = 0
        self.timings = {}

    def report(self):
        return {
            "queries": len(self.queries_executed),
            "raw_urls": self.raw_urls_extracted,
            "duplicates": self.duplicate_removals,
            "rejections": self.total_rejections,
            "retained": self.final_urls_retained,
            "timings": self.timings
        }

class SearchEngineManager:
    def __init__(self):
        self.health = {"duckduckgo": SearchHealth()}
        self.diagnostics = SearchDiagnostics()

    def _single_search(self, query: str) -> List[Dict]:
        """Perform a single DDG search with retries."""
        start = time.time()
        results = []
        try:
            with DDGS() as ddgs:
                ddgs_gen = ddgs.text(query, max_results=20)
                if ddgs_gen:
                    results = list(ddgs_gen)
            self.health["duckduckgo"].avg_latency = (self.health["duckduckgo"].avg_latency + (time.time() - start)) / 2
        except Exception as e:
            logger.warning(f"Search query failed '{query}': {e}")
            self.health["duckduckgo"].errors_429 += 1
        return results

    def search(self, queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
        overall_start = time.time()
        found = {}
        rejected = []
        seen_fingerprints = set()

        self.diagnostics.queries_executed = queries

        # Execute searches concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            all_raw_results_lists = list(executor.map(self._single_search, queries))

        # Flatten results and process
        for raw_results in all_raw_results_lists:
            self.diagnostics.raw_urls_extracted += len(raw_results)
            for r in raw_results:
                url = r.get("href")
                if not url: continue

                c_url = canonicalize_url(url)

                # Deduplication
                p = urlparse(c_url)
                fp = f"{p.netloc}{p.path}".lower()
                if fp in seen_fingerprints:
                    self.diagnostics.duplicate_removals += 1
                    continue
                seen_fingerprints.add(fp)

                info = get_source_v6_info(c_url, r.get("title", ""))
                if info.rejection_reason:
                    if "format" in info.rejection_reason:
                        self.diagnostics.unsupported_file_removals += 1
                    elif "Social" in info.rejection_reason or "Video" in info.rejection_reason:
                        self.diagnostics.blacklist_removals += 1
                    else:
                        self.diagnostics.total_rejections += 1
                    rejected.append(info)
                    continue

                if c_url not in found:
                    found[c_url] = {
                        "url": c_url,
                        "title": r.get("title", ""),
                        "score": info.score,
                        "tier": info.tier,
                        "source_type": info.type
                    }

        # Fallback Logic: If no results, try broader queries
        if not found and queries:
            logger.info("Primary search returned no results. Attempting fallback...")
            fallback_queries = [re.sub(r'site:\S+|"|\+', '', q).strip() for q in queries[:2]]
            fallback_results = []
            for fq in fallback_queries:
                if fq: fallback_results.extend(self._single_search(fq))

            for r in fallback_results:
                url = r.get("href")
                if not url: continue
                c_url = canonicalize_url(url)
                info = get_source_v6_info(c_url, r.get("title", ""))
                if not info.rejection_reason and c_url not in found:
                     found[c_url] = {"url": c_url, "title": r.get("title", ""), "score": info.score - 20, "tier": 5, "source_type": "Fallback"}

        # Final Ranking
        sorted_res = sorted(found.values(), key=lambda x: x["score"], reverse=True)
        final_list = sorted_res[:max_results_total]

        self.diagnostics.final_urls_retained = len(final_list)
        self.diagnostics.timings["total_search_ms"] = int((time.time() - overall_start) * 1000)

        # Structured Logging
        logger.info(f"Search Cycle Completed: {self.diagnostics.report()}")

        return final_list, rejected, self.health

def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS) -> Tuple[List[Dict], List[SourceV2Info], Dict[str, SearchHealth]]:
    """Production entry point for hardened search."""
    if isinstance(queries, str):
        queries = [queries]

    # Validation
    if not queries:
        return [], [], {"duckduckgo": SearchHealth(success_rate=0.0)}

    manager = SearchEngineManager()
    return manager.search(queries, max_results_total)
