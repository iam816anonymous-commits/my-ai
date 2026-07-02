import logging
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_text(html: str) -> str:
    """
    Extracts main article text from HTML using trafilatura with BeautifulSoup fallback.
    """
    if not html:
        return ""

    # Try trafilatura first
    # trafilatura.extract might return None if it can't find clear article structure
    extracted = trafilatura.extract(html, include_comments=False, include_tables=True, no_fallback=True)

    if extracted:
        return extracted

    # Fallback to BeautifulSoup
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts, styles, and common navigation/footer elements
        for element in soup.find_all(["script", "style", "nav", "footer", "aside", "header", "form", "button"]):
            element.decompose()

        # Also look for common classes/ids that usually contain nav/footer if they are not using semantic tags
        for unwanted in soup.find_all(attrs={"class": lambda x: x and any(word in x.lower() for word in ["nav", "footer", "sidebar", "menu", "ads"])}):
            unwanted.decompose()
        for unwanted in soup.find_all(attrs={"id": lambda x: x and any(word in x.lower() for word in ["nav", "footer", "sidebar", "menu", "ads"])}):
            unwanted.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        # Basic cleaning
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"BeautifulSoup extraction failed: {e}")
        return ""
