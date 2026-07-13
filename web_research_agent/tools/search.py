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
from web_research_agent.models.schemas import SourceV2Info, SearchHealth, PipelineResult, SearchResult

logger = logging.getLogger(__name__)

# Authoritative Tiers V6
TIER_1 = {
    "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org", "mit.edu", "stanford.edu", "harvard.edu", ".gov",
    "w3.org", "iso.org", "scholar.google.com", "semanticscholar.org", "ncbi.nlm.nih.gov", "ssrn.com", "sec.gov",
    "bls.gov", "bis.org", "ecb.europa.eu", "federareserve.gov"
}
TIER_2 = {
    "microsoft.com", "google.com", "openai.com", "anthropic.com", "nvidia.com", "github.com", "docs.", "developer.",
    "gartner.com", "mckinsey.com", "reuters.com", "apnews.com", "bloomberg.com", "ft.com", "wsj.com", "economist.com"
}
TIER_3 = {
    "bbc.com", "techcrunch.com", "wired.com", "verge.com", "infoworld.com", "zdnet.com", "eweek.com"
}

def canonicalize_url(url: str) -> str:
    """Standardizes URL to prevent duplicates."""
    try:
        p = urlparse(url)
        query_params = []
        if p.query:
            query_params = [q for q in p.query.split("&") if not any(x in q.lower() for x in ["utm_", "ref", "fbclid", "gclid", "source"])]
        new_url = urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), p.params, "&".join(query_params), ""))
        return new_url
    except:
        return url

def get_source_v7_info(url: str, title: str = "") -> SourceV2Info:
    """Harden source scoring with priority for high-authority domains."""
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

    # Strict Validation for Production Quality
    rej = None
    junk_patterns = ["/search?", "/login", "/signup", "cookie-policy", "captcha", "privacy-policy", "terms-of-service", "/categories/", "/tags/"]
    if any(x in url_lower for x in [".zip", ".exe", ".gz", ".docx", ".pptx"]):
        rej = "Unsupported binary format"
    elif any(p in url_lower for p in junk_patterns):
        rej = "Navigation/Administrative page"
    elif len(url_lower) < 15:
        rej = "URL too short (likely homepage)"
    elif any(x in netloc for x in ["linkedin.com", "facebook.com", "twitter.com", "instagram.com", "pinterest.com", "reddit.com"]):
        rej = "Social Media (Low Authority)"
    elif any(x in netloc for x in ["youtube.com", "vimeo.com", "tiktok.com"]):
        rej = "Video Platform"

    if str(time.localtime().tm_year) in url or str(time.localtime().tm_year) in title:
        score += 10

    return SourceV2Info(url=url, title=title, score=score, tier=tier, type=stype, rejection_reason=rej)

class SearchEngineManager:
    def __init__(self):
        self.health = {"duckduckgo": SearchHealth()}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    def _single_search(self, query: str) -> List[Dict]:
        results = []
        try:
            with DDGS() as ddgs:
                ddgs_gen = ddgs.text(query, max_results=20)
                if ddgs_gen:
                    results = list(ddgs_gen)
        except Exception as e:
            logger.warning(f"Search query failed '{query}': {e}")
        return results

    def search(self, queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS, original_query: str = "") -> PipelineResult[SearchResult]:
        start_time = time.time()
        found: Dict[str, SourceV2Info] = {}
        rejected: List[SourceV2Info] = []
        seen_fingerprints = set()

        try:
            with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
                all_raw_results_lists = list(executor.map(self._single_search, queries))

            for raw_results in all_raw_results_lists:
                for r in raw_results:
                    url = r.get("href")
                    if not url: continue
                    c_url = canonicalize_url(url)

                    p = urlparse(c_url)
                    fp = f"{p.netloc}{p.path}".lower()
                    if fp in seen_fingerprints: continue
                    seen_fingerprints.add(fp)

                    info = get_source_v7_info(c_url, r.get("title", ""))

                    # Deterministic Keyword Boost (Phase 1)
                    if original_query:
                        keywords = [k.lower() for k in original_query.split() if len(k) > 3]
                        title_lower = info.title.lower()
                        for k in keywords:
                            if k in title_lower:
                                info.score += 5
                            if k in c_url.lower():
                                info.score += 2

                    if info.rejection_reason:
                        rejected.append(info)
                        continue

                    if c_url not in found:
                        found[c_url] = info

            # Adaptive broad fallback if nothing found
            if not found:
                broad_queries = [re.sub(r'site:\S+|"|\+', '', q).strip() for q in queries[:2]]
                with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
                    fallback_lists = list(executor.map(self._single_search, broad_queries))
                for raw_results in fallback_lists:
                    for r in raw_results:
                        url = r.get("href")
                        if not url: continue
                        c_url = canonicalize_url(url)
                        info = get_source_v7_info(c_url, r.get("title", ""))
                        if not info.rejection_reason and c_url not in found:
                             info.type = "Fallback"
                             info.score -= 20
                             found[c_url] = info

            # Deterministic Ranking & Selection (Phase 1)
            sorted_res = sorted(found.values(), key=lambda x: x.score, reverse=True)
            final_list = sorted_res[:max_results_total]

            return PipelineResult(
                success=True,
                payload=SearchResult(scored_urls=final_list, rejected_urls=rejected, health=self.health),
                metrics={"urls_found": len(found), "urls_rejected": len(rejected)},
                timing=time.time() - start_time,
                stage="search"
            )
        except Exception as e:
            return PipelineResult(success=False, errors=[str(e)], stage="search", timing=time.time() - start_time)

def search_web(queries: List[str], max_results_total: int = MAX_SEARCH_RESULTS, original_query: str = "") -> PipelineResult[SearchResult]:
    if not isinstance(queries, list):
        return PipelineResult(success=False, errors=["Search queries must be a list"], stage="search")

    from web_research_agent.tools.cache import cache
    cache_key = f"search_{queries}_{max_results_total}_{original_query}"
    cached = cache.get(cache_key)
    if cached:
        logger.info("Search cache hit.")
        return PipelineResult(success=True, payload=SearchResult.model_validate(cached), stage="search")

    res = SearchEngineManager().search(queries, max_results_total, original_query)
    if res.success:
        cache.set(cache_key, res.payload.model_dump())
    return res
