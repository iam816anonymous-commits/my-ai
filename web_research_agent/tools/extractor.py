import logging
import trafilatura
from bs4 import BeautifulSoup
import re
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from web_research_agent.config import MAX_ARTICLE_CHARS, CONCURRENCY

logger = logging.getLogger(__name__)

def clean_html(html: str) -> str:
    """Aggressively cleans HTML."""
    if not html: return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer", "aside", "header", "form", "button", "iframe", "table", "thead", "tbody", "tfoot", "tr", "th", "td", "figure", "figcaption", "video", "audio", "input", "label"]):
        tag.decompose()
    patterns = re.compile(r"infobox|sidebar|nav|menu|footer|ad-|promo|social|comment|share|metadata|reference|reflist|mw-empty-elt|citation|hatnote|stub", re.I)
    for el in soup.find_all(attrs={"class": patterns}): el.decompose()
    for el in soup.find_all(attrs={"id": patterns}): el.decompose()
    return str(soup)

def deduplicate_text(text: str) -> str:
    """Removes duplicate paragraphs."""
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

def extract_text(html: str) -> str:
    """Extracts article text."""
    if not html: return ""
    # Speed optimization: check if already plain text (from PDF extract)
    if not html.strip().startswith("<"): return html[:MAX_ARTICLE_CHARS]

    try:
        cleaned = clean_html(html)
        extracted = trafilatura.extract(cleaned, include_comments=False, include_tables=False, fast=True)
        if not extracted or len(extracted) < 150:
            soup = BeautifulSoup(cleaned, "html.parser")
            extracted = soup.get_text(separator="\n")
        clean_text = deduplicate_text(extracted)
        return clean_text[:MAX_ARTICLE_CHARS]
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return ""

def extract_all(html_contents: Dict[str, str]) -> Dict[str, str]:
    """Parallel extraction."""
    results = {}
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        future_to_url = {executor.submit(extract_text, html): url for url, html in html_contents.items()}
        for future in future_to_url:
            url = future_to_url[future]
            try: results[url] = future.result()
            except: results[url] = ""
    return results
