import logging
import trafilatura
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
def extract_text(html: str) -> str:
    """
    Extracts main article text from HTML using trafilatura with BeautifulSoup fallback.
    Retries up to 2 times on internal errors.
    """
    if not html or len(html) < 100:
        logger.warning("Empty or too short HTML provided for extraction.")
        return ""

    try:
        # Try trafilatura first
        # trafilatura.extract is the main API
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True, no_fallback=True)

        if extracted and len(extracted) > 200:
            return extracted

        logger.info("Trafilatura extraction failed or too short, falling back to BeautifulSoup.")

        # Fallback to BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts, styles, and common navigation/footer elements
        for element in soup.find_all(["script", "style", "nav", "footer", "aside", "header", "form", "button"]):
            element.decompose()

        # Also look for common classes/ids that usually contain nav/footer if they are not using semantic tags
        for unwanted in soup.find_all(attrs={"class": lambda x: x and any(word in str(x).lower() for word in ["nav", "footer", "sidebar", "menu", "ads"])}):
            unwanted.decompose()
        for unwanted in soup.find_all(attrs={"id": lambda x: x and any(word in str(x).lower() for word in ["nav", "footer", "sidebar", "menu", "ads"])}):
            unwanted.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        # Basic cleaning
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        if len(clean_text) < 100:
            logger.warning("Extracted text is too short even after fallback.")
            return ""

        return clean_text

    except Exception as e:
        logger.error(f"Extraction attempt failed: {str(e)}")
        raise e
