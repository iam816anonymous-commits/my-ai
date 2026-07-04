import logging
import asyncio
import aiohttp
import io
import pypdf
from typing import List, Dict, Tuple, Optional
from web_research_agent.config import REQUEST_TIMEOUT, CONCURRENCY
from web_research_agent.tools.cache import cache

logger = logging.getLogger(__name__)

async def fetch_url_async(session: aiohttp.ClientSession, url: str) -> Tuple[str, str]:
    """Downloads a single URL with caching and error handling."""
    # Check cache first
    cached = cache.get(f"html_{url}")
    if cached:
        return url, cached

    headers = {"User-Agent": "Mozilla/5.0 (Analyst Research Agent Production)"}
    try:
        async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                # ArXiv HTML preference
                if "arxiv.org/pdf/" in url:
                    html_url = url.replace("/pdf/", "/html/").replace(".pdf", "")
                    try:
                        async with session.get(html_url, headers=headers, timeout=5) as h_resp:
                            if h_resp.status == 200:
                                text = await h_resp.text()
                                cache.set(f"html_{url}", text)
                                return url, text
                    except: pass

                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/pdf' in content_type or url.endswith('.pdf'):
                    content = await response.read()
                    text = extract_text_from_pdf(content)
                    cache.set(f"html_{url}", text)
                    return url, text

                text = await response.text()
                cache.set(f"html_{url}", text)
                return url, text
            return url, ""
    except Exception as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return url, ""

async def fetch_all_async(urls: List[str]) -> Dict[str, str]:
    """Parallel downloads with connection pooling."""
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_url_async(session, url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return {url: content for url, content in responses}

def fetch_all(urls: List[str], max_workers: int = CONCURRENCY) -> Dict[str, str]:
    """Synchronous wrapper for async fetch pipeline."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(fetch_all_async(urls))

def extract_text_from_pdf(content: bytes) -> str:
    try:
        pdf_file = io.BytesIO(content)
        reader = pypdf.PdfReader(pdf_file)
        return "\n".join([p.extract_text() for p in reader.pages])
    except Exception as e:
        logger.error(f"PDF extract error: {e}")
        return ""
