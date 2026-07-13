import logging
import time
import trafilatura
from bs4 import BeautifulSoup
import re
import hashlib
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from web_research_agent.config import MAX_ARTICLE_CHARS, CONCURRENCY
from web_research_agent.tools.cache import cache
from web_research_agent.models.schemas import PipelineResult, ExtractionResult

logger = logging.getLogger(__name__)

def clean_html_v2(html: str) -> str:
    """Production-grade HTML noise reduction."""
    if not html: return ""
    soup = BeautifulSoup(html, "html.parser")
    # Aggressive tag removal
    for tag in soup.find_all(["script", "style", "nav", "footer", "aside", "header", "form", "button", "iframe", "table", "figure", "input", "label", "svg", "noscript"]):
        tag.decompose()

    # Class/ID patterns for boilerplate
    patterns = re.compile(r"infobox|sidebar|nav|menu|footer|ad-|promo|social|comment|share|metadata|reference|reflist|mw-empty-elt|citation|cookie|policy|consent|banner|toolbar", re.I)
    for el in soup.find_all(attrs={"class": patterns}): el.decompose()
    for el in soup.find_all(attrs={"id": patterns}): el.decompose()

    return str(soup)

def is_junk_v2(text: str) -> bool:
    """Improved junk detection to prevent placeholder pages."""
    if not text or len(text) < 300: return True

    junk_patterns = [
        r"enable cookies", r"javascript is required", r"access denied", r"verify you are a human",
        r"captcha", r"robot test", r"403 forbidden", r"404 not found", r"security challenge",
        r"just a moment", r"cookie policy", r"agree to our use of cookies", r"sign in to your account"
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in junk_patterns)

def extract_text_v2(html: str) -> str:
    """Extracts structured content with caching."""
    if not html: return ""

    stable_hash = hashlib.sha256(html.encode('utf-8')).hexdigest()
    content_key = f"extract_v2_{stable_hash}"
    cached = cache.get(content_key)
    if cached: return cached

    try:
        # Fallback for plain text (e.g. PDF extraction result)
        if not html.strip().startswith("<"):
            text = html[:MAX_ARTICLE_CHARS]
            if is_junk_v2(text): return ""
            cache.set(content_key, text)
            return text

        cleaned = clean_html_v2(html)
        # Use trafilatura with specific flags for article extraction
        extracted = trafilatura.extract(
            cleaned,
            include_comments=False,
            include_tables=False,
            include_images=False,
            no_fallback=False
        )

        if not extracted or len(extracted) < 200:
            soup = BeautifulSoup(cleaned, "html.parser")
            extracted = soup.get_text(separator="\n\n")

        # Clean extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', extracted).strip()
        final_text = text[:MAX_ARTICLE_CHARS]

        if is_junk_v2(final_text):
            return ""

        cache.set(content_key, final_text)
        return final_text
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return ""

import math
from collections import Counter

def validate_semantic_relevance_deterministic(text: str, query: str) -> bool:
    """Deterministic semantic check using native Cosine Similarity (Phase 2)."""
    if not text or not query: return False

    try:
        def get_cosine(vec1, vec2):
            intersection = set(vec1.keys()) & set(vec2.keys())
            numerator = sum([vec1[x] * vec2[x] for x in intersection])

            sum1 = sum([vec1[x]**2 for x in vec1.keys()])
            sum2 = sum([vec2[x]**2 for x in vec2.keys()])
            denominator = math.sqrt(sum1) * math.sqrt(sum2)

            if not denominator:
                return 0.0
            else:
                return float(numerator) / denominator

        def text_to_vector(t):
            words = re.findall(r'\w+', t.lower())
            return Counter(words)

        vector1 = text_to_vector(query)
        vector2 = text_to_vector(text)

        similarity = get_cosine(vector1, vector2)

        # Threshold for relevance. 0.05 is conservative for word-based similarity
        return similarity > 0.05
    except Exception as e:
        logger.warning(f"Deterministic semantic validation error: {e}")
        return True

def extract_all(html_contents: Dict[str, str], query: str = "") -> PipelineResult[ExtractionResult]:
    """Parallel extraction with stage metrics and validation."""
    start_time = time.time()
    results = {}
    valid_count = 0
    rejected_count = 0

    try:
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            future_to_url = {executor.submit(extract_text_v2, html): url for url, html in html_contents.items()}
            for future in future_to_url:
                url = future_to_url[future]
                try:
                    text = future.result()
                    if text:
                        if query:
                            if not validate_semantic_relevance_deterministic(text, query):
                                logger.info(f"Rejected irrelevant content deterministically: {url}")
                                rejected_count += 1
                                results[url] = ""
                                continue
                        results[url] = text
                        valid_count += 1
                    else:
                        results[url] = ""
                        rejected_count += 1
                except:
                    results[url] = ""
                    rejected_count += 1

        return PipelineResult(
            success=True,
            payload=ExtractionResult(texts_map=results, valid_count=valid_count, rejected_count=rejected_count),
            timing=time.time() - start_time,
            stage="extraction"
        )
    except Exception as e:
        return PipelineResult(success=False, errors=[str(e)], stage="extraction", timing=time.time() - start_time)
