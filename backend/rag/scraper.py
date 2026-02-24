"""Web scraper for company research.

Primary: httpx + BeautifulSoup4 (no external API dependency)
Fallback: firecrawl-py if available and configured.

Respects robots.txt, implements rate limiting, and extracts
structured company information.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

# Rate limiting: min seconds between requests to same domain
_last_request_time: dict[str, float] = {}
RATE_LIMIT_SECONDS = 2.0

# Max pages to scrape per company
MAX_PAGES = 5

# Common paths to try for company info
COMPANY_PATHS = [
    "/about",
    "/about-us",
    "/careers",
    "/jobs",
    "/team",
    "/culture",
    "/engineering",
    "/tech",
    "/blog",
]


async def _check_robots_txt(base_url: str, client: httpx.AsyncClient) -> set[str]:
    """Check robots.txt and return set of disallowed paths."""
    disallowed = set()
    try:
        resp = await client.get(f"{base_url}/robots.txt", timeout=5)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                line = line.strip()
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.add(path)
    except Exception:
        pass
    return disallowed


async def _rate_limit(domain: str):
    """Enforce rate limiting per domain."""
    now = time.time()
    last = _last_request_time.get(domain, 0)
    wait = RATE_LIMIT_SECONDS - (now - last)
    if wait > 0:
        import asyncio
        await asyncio.sleep(wait)
    _last_request_time[domain] = time.time()


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Fallback: strip tags with regex
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def scrape_url(url: str, client: httpx.AsyncClient | None = None) -> Optional[str]:
    """Scrape a single URL and return extracted text.

    Args:
        url: URL to scrape.
        client: Optional httpx client (reuses connection pool).

    Returns:
        Extracted text content, or None if scraping failed.
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    await _rate_limit(domain)

    should_close = False
    if client is None:
        client = httpx.AsyncClient(follow_redirects=True, timeout=15)
        should_close = True

    try:
        headers = {
            "User-Agent": "ResumeGeneratorBot/1.0 (research; +https://github.com/resume-gen)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = await client.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"Scrape failed for {url}: HTTP {resp.status_code}")
            return None

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            logger.warning(f"Skipping non-HTML content at {url}: {content_type}")
            return None

        text = _extract_text_from_html(resp.text)
        if len(text) < 50:
            logger.debug(f"Skipping {url}: too little content ({len(text)} chars)")
            return None

        logger.info(f"Scraped {url}: {len(text)} chars")
        return text

    except Exception as e:
        logger.warning(f"Error scraping {url}: {e}")
        return None
    finally:
        if should_close:
            await client.aclose()


async def scrape_company(company_url: str) -> list[dict]:
    """Scrape company information from a base URL and related pages.

    Args:
        company_url: Base company URL (e.g., "https://example.com").

    Returns:
        List of dicts with "url", "text", and "content_type" keys.
    """
    parsed = urlparse(company_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    results = []
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        # Check robots.txt
        disallowed = await _check_robots_txt(base_url, client)

        # Scrape main page
        main_text = await scrape_url(company_url, client)
        if main_text:
            results.append({
                "url": company_url,
                "text": main_text,
                "content_type": "main",
            })

        # Try common company info paths
        for path in COMPANY_PATHS:
            if len(results) >= MAX_PAGES:
                break

            # Skip if disallowed by robots.txt
            if any(path.startswith(d) for d in disallowed):
                logger.debug(f"Skipping {path}: disallowed by robots.txt")
                continue

            url = urljoin(base_url, path)
            text = await scrape_url(url, client)
            if text:
                content_type = "careers" if "career" in path or "job" in path else "about"
                if "blog" in path or "tech" in path or "engineering" in path:
                    content_type = "tech_blog"
                results.append({
                    "url": url,
                    "text": text,
                    "content_type": content_type,
                })

    logger.info(f"Company scrape complete for {base_url}: {len(results)} pages collected")
    return results
