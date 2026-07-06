import logging
import trafilatura
from bs4 import BeautifulSoup
import re
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from web_research_agent.config import MAX_ARTICLE_CHARS, CONCURRENCY
from web_research_agent.tools.cache import cache

logger = logging.getLogger(__name__)

def clean_html(html: str) -> str:
    """Aggressive HTML noise reduction."""
    if not html: return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer", "aside", "header", "form", "button", "iframe", "table", "figure", "input", "label"]):
        tag.decompose()
    patterns = re.compile(r"infobox|sidebar|nav|menu|footer|ad-|promo|social|comment|share|metadata|reference|reflist|mw-empty-elt|citation", re.I)
    for el in soup.find_all(attrs={"class": patterns}): el.decompose()
    for el in soup.find_all(attrs={"id": patterns}): el.decompose()
    return str(soup)

def deduplicate_text(text: str) -> str:
    """Similarity-based paragraph deduplication."""
    paragraphs = text.split('\n\n')
    seen, unique = set(), []
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean: continue
        norm = re.sub(r'\W+', '', p_clean.lower())
        if norm not in seen:
            seen.add(norm)
            unique.append(p_clean)
    return '\n\n'.join(unique)

import hashlib

def is_junk_content(text: str, html: str) -> bool:
    """Detects if content is a placeholder, cookie banner, or nav-only page."""
    if not text or len(text) < 200: return True

    junk_patterns = [
        r"enable cookies", r"javascript is required", r"access denied",
        r"verify you are a human", r"captcha", r"robot test",
        r"403 forbidden", r"404 not found", r"security challenge",
        r"just a moment", r"please wait while we verify",
        r"cookie policy", r"agree to our use of cookies",
        r"sign in to your account", r"forgot password"
    ]

    text_lower = text.lower()
    if any(re.search(p, text_lower) for p in junk_patterns):
        return True

    # Check for search result pages
    if "results for" in text_lower and ("next page" in text_lower or "previous page" in text_lower):
        return True

    return False

def extract_text(html: str) -> str:
    """Professional article extraction with caching."""
    if not html: return ""

    # Check cache for clean text
    stable_hash = hashlib.sha256(html.encode('utf-8')).hexdigest()
    content_hash = f"extract_{stable_hash}"
    cached = cache.get(content_hash)
    if cached: return cached

    # If it's already plain text (from PDF)
    if not html.strip().startswith("<"):
        text = html[:MAX_ARTICLE_CHARS]
        if is_junk_content(text, ""): return ""
        cache.set(content_hash, text)
        return text

    try:
        cleaned = clean_html(html)
        extracted = trafilatura.extract(cleaned, include_comments=False, include_tables=False, fast=True)
        if not extracted or len(extracted) < 150:
            soup = BeautifulSoup(cleaned, "html.parser")
            extracted = soup.get_text(separator="\n")

        clean_text = deduplicate_text(extracted)[:MAX_ARTICLE_CHARS]

        if is_junk_content(clean_text, html):
            return ""

        cache.set(content_hash, clean_text)
        return clean_text
    except Exception as e:
        logger.error(f"Extract fail: {e}")
        return ""

def validate_semantic_relevance(text: str, query: str, llm_client) -> bool:
    """Verifies if the extracted text is relevant to the research query."""
    if not text or not query: return False

    prompt = f"""
    Research Query: {query}

    Extracted Text Fragment:
    {text[:1000]}

    Is this content semantically relevant to the research query?
    Exclude generic homepages, cookie walls, search result lists, or unrelated platforms (e.g., YouTube pages for non-video research).

    Answer with only "YES" or "NO".
    """
    try:
        response = llm_client.summarize(prompt).strip().upper()
        return "YES" in response
    except Exception as e:
        logger.warning(f"Semantic validation failed: {e}")
        return True # Fallback to true to avoid missing data on API error

def extract_all(html_contents: Dict[str, str], query: str = "", llm_client = None) -> Dict[str, str]:
    """Parallel extraction with optional semantic validation."""
    results = {}
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        future_to_url = {executor.submit(extract_text, html): url for url, html in html_contents.items()}
        for future in future_to_url:
            url = future_to_url[future]
            try:
                text = future.result()
                if text and query and llm_client:
                    if not validate_semantic_relevance(text, query, llm_client):
                        logger.info(f"Rejected unrelated content: {url}")
                        text = ""
                results[url] = text
            except:
                results[url] = ""
    return results
