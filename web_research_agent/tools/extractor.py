import logging
import trafilatura
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

def extract_text(html: str) -> str:
    """
    Extracts main article text from HTML using trafilatura with BeautifulSoup fallback.
    Limit to first 4000 chars for token optimization.
    """
    if not html:
        return ""

    try:
        # Use newer trafilatura API correctly
        # trafilatura.extract is standard
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True, no_fallback=True)

        if not extracted or len(extracted) < 100:
            logger.info("Trafilatura failed, using BeautifulSoup fallback.")
            soup = BeautifulSoup(html, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "aside", "header"]):
                element.decompose()
            extracted = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = [line.strip() for line in extracted.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        # Token optimization: limit to 4000 characters
        return clean_text[:4000]

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return ""
