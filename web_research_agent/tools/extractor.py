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
        cache.set(content_hash, text)
        return text

    try:
        cleaned = clean_html(html)
        extracted = trafilatura.extract(cleaned, include_comments=False, include_tables=False, fast=True)
        if not extracted or len(extracted) < 150:
            soup = BeautifulSoup(cleaned, "html.parser")
            extracted = soup.get_text(separator="\n")

        clean_text = deduplicate_text(extracted)[:MAX_ARTICLE_CHARS]
        cache.set(content_hash, clean_text)
        return clean_text
    except Exception as e:
        logger.error(f"Extract fail: {e}")
        return ""

def extract_all(html_contents: Dict[str, str]) -> Dict[str, str]:
    """Parallel extraction using ProcessPoolExecutor for CPU-bound cleaning."""
    results = {}
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        future_to_url = {executor.submit(extract_text, html): url for url, html in html_contents.items()}
        for future in future_to_url:
            url = future_to_url[future]
            try: results[url] = future.result()
            except: results[url] = ""
    return results
