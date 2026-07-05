import logging
import asyncio
import aiohttp
import io
import pypdf
import time
from typing import List, Dict, Tuple, Optional
from web_research_agent.config import REQUEST_TIMEOUT, MAX_RETRIES, CONCURRENCY
from web_research_agent.tools.cache import cache

logger = logging.getLogger(__name__)

async def fetch_url_async(session: aiohttp.ClientSession, url: str, attempt: int = 1) -> Tuple[str, str, float]:
    """Downloads a single URL with async speed, metrics, and robust retries."""
    cached = cache.get(f"html_{url}")
    if cached:
        return url, cached, 0.0

    headers = {"User-Agent": "Mozilla/5.0 (Analyst Autonomous Research Platform v1)"}
    start = time.time()
    try:
        async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
            latency = time.time() - start

            # Robust Retry Logic (429, 503, 504)
            if response.status in [429, 503, 504] and attempt <= 2:
                wait = (attempt ** 2) * 5
                logger.warning(f"Rate limited/Server error ({response.status}) for {url}. Waiting {wait}s...")
                await asyncio.sleep(wait)
                return await fetch_url_async(session, url, attempt + 1)

            if response.status == 200:
                # ArXiv HTML preference
                if "arxiv.org/pdf/" in url:
                    html_url = url.replace("/pdf/", "/html/").replace(".pdf", "")
                    try:
                        async with session.get(html_url, headers=headers, timeout=5) as h_resp:
                            if h_resp.status == 200:
                                text = await h_resp.text()
                                cache.set(f"html_{url}", text)
                                return url, text, latency
                    except: pass

                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/pdf' in content_type or url.endswith('.pdf'):
                    content = await response.read()
                    text = extract_text_from_pdf(content)
                    cache.set(f"html_{url}", text)
                    return url, text, latency

                text = await response.text()
                cache.set(f"html_{url}", text)
                return url, text, latency
            return url, "", latency
    except Exception as e:
        logger.warning(f"Async fetch failed for {url}: {e}")
        return url, "", time.time() - start

async def fetch_all_async(urls: List[str]) -> Tuple[Dict[str, str], float]:
    """Parallel downloads with total latency tracking."""
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    total_http_latency = 0.0
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_url_async(session, url) for url in urls]
        responses = await asyncio.gather(*tasks)
        results = {}
        for url, content, lat in responses:
            results[url] = content
            total_http_latency += lat
        return results, total_http_latency

def fetch_all(urls: List[str], max_workers: int = CONCURRENCY) -> Tuple[Dict[str, str], float]:
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
    except: return ""
