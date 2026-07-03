import logging
import requests
import io
import asyncio
import aiohttp
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
from web_research_agent.config import REQUEST_TIMEOUT, MAX_RETRIES, CONCURRENCY
import pypdf

logger = logging.getLogger(__name__)

# Cache for extractions and summaries (simulated in memory)
_extraction_cache = {}

def get_cached_extraction(url: str) -> Optional[str]:
    return _extraction_cache.get(url)

def cache_extraction(url: str, text: str):
    _extraction_cache[url] = text

async def fetch_url_async(session: aiohttp.ClientSession, url: str) -> Tuple[str, str]:
    """Async fetch for improved performance."""
    headers = {"User-Agent": "Mozilla/5.0 (Analyst Research Agent)"}
    try:
        async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                # Handle ArXiv HTML preference
                if "arxiv.org/pdf/" in url:
                    html_url = url.replace("/pdf/", "/html/").replace(".pdf", "")
                    try:
                        async with session.get(html_url, headers=headers, timeout=5) as h_resp:
                            if h_resp.status == 200:
                                return url, await h_resp.text()
                    except: pass

                if 'application/pdf' in response.headers.get('Content-Type', '').lower():
                    content = await response.read()
                    return url, "PDF_CONTENT:" + content.hex() # Marker for sync processing

                return url, await response.text()
            return url, ""
    except Exception as e:
        logger.error(f"Async fetch failed for {url}: {e}")
        return url, ""

async def fetch_all_async(urls: List[str]) -> Dict[str, str]:
    """Orchestrates async downloads."""
    results = {}
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url_async(session, url) for url in urls]
        responses = await asyncio.gather(*tasks)
        for url, content in responses:
            results[url] = content
    return results

def fetch_all(urls: List[str], max_workers: int = CONCURRENCY) -> Dict[str, str]:
    """Wrapper to run async loop in sync environment."""
    # Check cache first
    needed_urls = [u for u in urls if u not in _extraction_cache]

    if not needed_urls:
        return {u: "CACHED" for u in urls}

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    fetched = loop.run_until_complete(fetch_all_async(needed_urls))

    # Process PDF markers synchronously
    from web_research_agent.tools.browser import extract_text_from_pdf
    for url, content in fetched.items():
        if isinstance(content, str) and content.startswith("PDF_CONTENT:"):
            hex_data = content.split(":", 1)[1]
            fetched[url] = extract_text_from_pdf(bytes.fromhex(hex_data))

    return fetched

def extract_text_from_pdf(content: bytes) -> str:
    try:
        pdf_file = io.BytesIO(content)
        reader = pypdf.PdfReader(pdf_file)
        return "\n".join([p.extract_text() for p in reader.pages])
    except: return ""
