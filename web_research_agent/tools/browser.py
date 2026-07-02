import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from web_research_agent.config import REQUEST_TIMEOUT, MAX_RETRIES

logger = logging.getLogger(__name__)

# Global session with connection pooling
_session = None

def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
    return _session

def fetch_html(url: str, timeout: int = REQUEST_TIMEOUT) -> str:
    """
    Downloads webpage content using connection pooling and retries.
    """
    session = get_session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # Check for ArXiv HTML conversion preference if it's a PDF
        if url.endswith(".pdf") and "arxiv.org/pdf/" in url:
            html_url = url.replace("arxiv.org/pdf/", "arxiv.org/abs/").rstrip(".pdf")
            logger.info(f"Detected ArXiv PDF, attempting to get HTML version from {html_url}")
            # This is a bit recursive/circular but works for this specific case
            # In a real app we'd handle ArXiv HTML conversion via their experimental /html/ endpoint
            # but for now let's just use the landing page if the PDF is the direct link
            # Actually, ArXiv now supports HTML directly: https://arxiv.org/html/...
            alt_url = url.replace("/pdf/", "/html/").replace(".pdf", "")
            try:
                alt_resp = session.get(alt_url, headers=headers, timeout=timeout)
                if alt_resp.status_code == 200:
                    return alt_resp.text
            except:
                pass

        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return ""

def fetch_all(urls: List[str], max_workers: int = 5) -> Dict[str, str]:
    """
    Downloads multiple webpages in parallel.
    """
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(fetch_html, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                content = future.result()
                results[url] = content
            except Exception as e:
                logger.error(f"Parallel fetch failed for {url}: {e}")
                results[url] = ""
    return results
