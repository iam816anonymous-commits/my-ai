import logging
import trafilatura
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

def clean_html(html: str) -> str:
    """
    Aggressively cleans HTML by removing non-article elements.
    Preserves lists as they often contain valuable research data.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Elements to remove
    unwanted_tags = [
        "script", "style", "nav", "footer", "aside", "header", "form", "button",
        "iframe", "table", "thead", "tbody", "tfoot", "tr", "th", "td"
    ]

    for tag in soup.find_all(unwanted_tags):
        tag.decompose()

    # Remove by class/id (infoboxes, sidebar, etc)
    unwanted_patterns = re.compile(
        r"infobox|sidebar|nav|menu|footer|ad-|promo|social|comment|share|metadata|reference|reflist|mw-empty-elt",
        re.I
    )

    for element in soup.find_all(class_=unwanted_patterns):
        element.decompose()
    for element in soup.find_all(id=unwanted_patterns):
        element.decompose()

    return str(soup)

def deduplicate_text(text: str) -> str:
    """
    Removes duplicate paragraphs and sentences.
    """
    paragraphs = text.split('\n\n')
    seen_paragraphs = set()
    unique_paragraphs = []

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue

        # Simple similarity: normalize and check
        p_norm = re.sub(r'\W+', '', p_clean.lower())
        if p_norm not in seen_paragraphs:
            seen_paragraphs.add(p_norm)
            unique_paragraphs.append(p_clean)

    return '\n\n'.join(unique_paragraphs)

def extract_text(html: str) -> str:
    """
    Extracts article text with professional quality.
    """
    if not html:
        return ""

    try:
        # Pre-clean HTML
        cleaned_html = clean_html(html)

        # Try trafilatura
        extracted = trafilatura.extract(cleaned_html, include_comments=False, include_tables=False, no_fallback=True)

        if not extracted or len(extracted) < 200:
            logger.info("Trafilatura failed or too short, falling back to BeautifulSoup.")
            soup = BeautifulSoup(cleaned_html, "html.parser")
            extracted = soup.get_text(separator="\n")

        # Post-process
        clean_text = deduplicate_text(extracted)

        # Token optimization
        return clean_text[:4000]

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return ""
