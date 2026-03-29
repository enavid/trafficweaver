"""
    browser.py – Simulate human browsing.

    Two backends:
      1. aiohttp + BeautifulSoup (lightweight, default)
      2. Playwright Chromium (harder to fingerprint as a bot, optional)

    The Playwright backend is used when cfg.use_playwright is True and the
    `playwright` package is installed.
"""

from __future__ import annotations

import asyncio
import random
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from config import Config
from logger import get_logger

log = get_logger("browser")


# Shared helpers

_DESKTOP_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

_ACCEPT_LANGS = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.8,fa;q=0.5",
    "en-CA,en;q=0.9",
]


def _build_headers(referer: Optional[str] = None) -> dict:
    headers = {
        "User-Agent": random.choice(_DESKTOP_UAS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(_ACCEPT_LANGS),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none" if referer is None else "same-origin",
        "Connection": "keep-alive",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _extract_internal_links(html: str, base_url: str, max_links: int) -> List[str]:
    """Pick up to max_links internal links from the page."""
    if max_links == 0:
        return []
    soup = BeautifulSoup(html, "lxml")
    base_domain = urlparse(base_url).netloc
    candidates: List[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
            candidates.append(full)
    if not candidates:
        return []
    random.shuffle(candidates)
    return candidates[:max_links]


# aiohttp backend

async def _fetch_page_aiohttp(
    session: aiohttp.ClientSession,
    url: str,
    referer: Optional[str] = None,
) -> Optional[str]:
    try:
        async with session.get(url, headers=_build_headers(referer), allow_redirects=True) as resp:
            if resp.status == 200:
                return await resp.text(errors="replace")
            log.debug("Non-200 response | url=%s | status=%d", url, resp.status)
    except Exception as exc:
        log.debug("Fetch error | url=%s | error=%s", url, exc)
    return None


async def browse_site_aiohttp(url: str, cfg: Config) -> int:
    """
    Visit `url` and follow a few internal links.
    Returns total bytes received (approximated from text length).
    """
    timeout = aiohttp.ClientTimeout(total=30)
    jar = aiohttp.CookieJar()
    total_bytes = 0

    connector = aiohttp.TCPConnector(local_addr=(cfg.bind_ip, 0)) if cfg.bind_ip else None
    async with aiohttp.ClientSession(cookie_jar=jar, connector=connector, timeout=timeout) as session:
        log.info("Browsing | url=%s | backend=aiohttp", url)

        html = await _fetch_page_aiohttp(session, url)
        if html is None:
            return 0
        total_bytes += len(html.encode("utf-8", errors="replace"))
        log.debug("Page loaded | url=%s | bytes=%d", url, total_bytes)

        links = _extract_internal_links(html, url, cfg.browse_max_internal_links)
        for link in links:
            delay = random.uniform(*cfg.browse_delay_range)
            log.debug("Waiting before next page | delay=%.1fs", delay)
            await asyncio.sleep(delay)

            sub_html = await _fetch_page_aiohttp(session, link, referer=url)
            if sub_html:
                total_bytes += len(sub_html.encode("utf-8", errors="replace"))
                log.debug("Sub-page loaded | url=%s | bytes=%d", link, len(sub_html))

    log.info("Browse complete | url=%s | total_bytes=%d", url, total_bytes)
    return total_bytes


# Playwright backend

async def browse_site_playwright(url: str, cfg: Config) -> int:
    """
    Visit `url` using a real Chromium instance via Playwright.
    Mimics human behaviour: random viewport, slow scrolling, realistic delays.
    Returns total bytes received.
    """
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        log.warning("Playwright not installed; falling back to aiohttp backend.")
        return await browse_site_aiohttp(url, cfg)

    total_bytes = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=random.choice(_DESKTOP_UAS),
            viewport={"width": random.randint(1280, 1920), "height": random.randint(768, 1080)},
            locale=random.choice(["en-US", "en-GB"]),
            timezone_id="Europe/London",
            java_script_enabled=True,
            accept_downloads=False,
        )
        page = await ctx.new_page()

        # Track response sizes
        page.on("response", lambda r: None)  # placeholder – byte counting below

        log.info("Browsing | url=%s | backend=playwright", url)

        async def _navigate(target: str, referer: Optional[str] = None) -> Optional[str]:
            nonlocal total_bytes
            try:
                options = {"wait_until": "domcontentloaded", "timeout": 30_000}
                if referer:
                    options["referer"] = referer  # type: ignore[assignment]
                await page.goto(target, **options)

                # Human-like scroll behaviour
                await asyncio.sleep(random.uniform(1.5, 4.0))
                for _ in range(random.randint(2, 6)):
                    await page.mouse.wheel(0, random.randint(200, 600))
                    await asyncio.sleep(random.uniform(0.3, 1.5))

                content = await page.content()
                total_bytes += len(content.encode("utf-8", errors="replace"))
                return content
            except Exception as exc:
                log.debug("Playwright nav error | url=%s | error=%s", target, exc)
                return None

        html = await _navigate(url)
        if html:
            links = _extract_internal_links(html, url, cfg.browse_max_internal_links)
            for link in links:
                delay = random.uniform(*cfg.browse_delay_range)
                await asyncio.sleep(delay)
                await _navigate(link, referer=url)

        await browser.close()

    log.info("Browse complete | url=%s | total_bytes=%d | backend=playwright", url, total_bytes)
    return total_bytes


# Public entry point

async def browse_site(url: str, cfg: Config) -> int:
    if cfg.use_playwright:
        return await browse_site_playwright(url, cfg)
    return await browse_site_aiohttp(url, cfg)
