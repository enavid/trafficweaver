"""
    browser_engine.py — Smart browsing with configurable multi-level depth.

    Two backends:
      1. aiohttp + BeautifulSoup (lightweight, default)
      2. Playwright Chromium (harder to fingerprint, optional)

    Features:
      - Multi-level depth crawling (1-3 levels)
      - Human-like behaviours: random delays, scroll simulation, reading time
      - Proper Referer headers
      - Random chance to "go back" to parent page
      - Max ~10-15 pages per site visit regardless of depth
      - Page title extraction and live browsing notification callbacks
"""

from __future__ import annotations

import random
import asyncio
import re
import aiohttp
from typing import Callable, Coroutine, List, Optional, Set
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from backend.domain.entities import BrowseResult, BrowseUpdate, Config
from backend.infrastructure.logging.log_handler import get_logger

log = get_logger("browser")

# Maximum total pages per site visit to keep traffic reasonable
_MAX_PAGES_PER_VISIT = 15

# ── Shared helpers ────────────────────────────────────────────────────────────

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


# Type alias for the optional browse update callback
BrowseCallback = Optional[Callable[[BrowseUpdate], Coroutine]]


def _build_headers(referer: Optional[str] = None) -> dict:
    """Build realistic browser request headers."""
    headers = {
        "User-Agent": random.choice(_DESKTOP_UAS),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
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


def _extract_title(html: str) -> str:
    """Extract the page title from HTML content."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()[:200]
    return ""


def _extract_internal_links(
    html: str, base_url: str, max_links: int
) -> List[str]:
    """Pick up to max_links internal links from the page."""
    if max_links == 0:
        return []
    soup = BeautifulSoup(html, "lxml")
    base_domain = urlparse(base_url).netloc
    candidates: List[str] = []
    seen: Set[str] = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        # Only same-domain HTTP(S) links
        if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if normalized not in seen:
                seen.add(normalized)
                candidates.append(full)
    if not candidates:
        return []
    random.shuffle(candidates)
    return candidates[:max_links]


def _simulate_reading_delay(html_length: int) -> float:
    """Compute a realistic reading delay based on content length."""
    # Average reading speed ~250 words/min, ~5 chars/word
    words_estimate = html_length / 5
    reading_time = words_estimate / 250 * 60  # seconds
    # Cap between 2 and 15 seconds, with randomness
    base = min(max(reading_time * 0.05, 2.0), 15.0)
    return base * random.uniform(0.6, 1.4)


async def _notify(
    callback: BrowseCallback, url: str, title: str, depth: int
) -> None:
    """Send a browse update notification if a callback is registered."""
    if callback is None:
        return
    update = BrowseUpdate(
        url=url,
        title=title,
        depth=depth,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    try:
        await callback(update)
    except Exception:
        pass


# ── aiohttp backend ──────────────────────────────────────────────────────────


async def _fetch_page_aiohttp(
    session: aiohttp.ClientSession,
    url: str,
    referer: Optional[str] = None,
) -> Optional[str]:
    """Fetch a single page via aiohttp. Returns HTML or None on failure."""
    try:
        async with session.get(
            url, headers=_build_headers(referer), allow_redirects=True
        ) as resp:
            if resp.status == 200:
                return await resp.text(errors="replace")
            log.debug("Non-200 response | url=%s | status=%d", url, resp.status)
    except Exception as exc:
        log.debug("Fetch error | url=%s | error=%s", url, exc)
    return None


async def browse_site_aiohttp(
    url: str,
    cfg: Config,
    on_page: BrowseCallback = None,
) -> BrowseResult:
    """
    Visit ``url`` and follow internal links up to ``browse_depth`` levels.

    Returns a BrowseResult with total bytes and pages visited.
    """
    result = BrowseResult(url=url)
    timeout = aiohttp.ClientTimeout(total=30)
    jar = aiohttp.CookieJar()

    connector = (
        aiohttp.TCPConnector(local_addr=(cfg.bind_ip, 0))
        if cfg.bind_ip
        else None
    )

    max_depth = max(1, min(3, cfg.browse_depth))
    links_per_page = max(1, min(3, cfg.browse_max_internal_links))
    visited: Set[str] = set()

    async with aiohttp.ClientSession(
        cookie_jar=jar, connector=connector, timeout=timeout
    ) as session:
        log.info("Browsing | url=%s | backend=aiohttp | depth=%d", url, max_depth)

        async def _visit_page(
            page_url: str,
            depth: int,
            referer_url: Optional[str],
        ) -> None:
            """Recursively visit a page and its internal links."""
            if result.pages_visited >= _MAX_PAGES_PER_VISIT:
                return
            if page_url in visited:
                return

            visited.add(page_url)

            html = await _fetch_page_aiohttp(session, page_url, referer=referer_url)
            if html is None:
                return

            page_bytes = len(html.encode("utf-8", errors="replace"))
            result.total_bytes += page_bytes
            result.pages_visited += 1
            result.max_depth_reached = max(result.max_depth_reached, depth)

            title = _extract_title(html)
            log.info(
                "Page loaded | url=%s | depth=%d | bytes=%d | title=%s",
                page_url, depth, page_bytes, title[:60],
            )

            await _notify(on_page, page_url, title, depth)

            # Simulate reading time with random variation
            read_delay = _simulate_reading_delay(len(html))
            await asyncio.sleep(read_delay)

            # Random small delays to simulate scrolling
            scroll_count = random.randint(1, 3)
            for _ in range(scroll_count):
                await asyncio.sleep(random.uniform(0.3, 1.2))

            # Follow internal links if we have depth remaining
            if depth < max_depth and result.pages_visited < _MAX_PAGES_PER_VISIT:
                links = _extract_internal_links(html, page_url, links_per_page)
                for link in links:
                    if result.pages_visited >= _MAX_PAGES_PER_VISIT:
                        break

                    # Random delay between pages (non-uniform timing)
                    delay = random.uniform(*cfg.browse_delay_range)
                    # Add jitter to prevent uniform intervals
                    delay *= random.uniform(0.7, 1.3)
                    log.debug("Waiting before next page | delay=%.1fs", delay)
                    await asyncio.sleep(delay)

                    # Random chance to "go back" to parent before clicking
                    if random.random() < 0.25 and referer_url:
                        back_delay = random.uniform(1.0, 3.0)
                        log.debug(
                            "Simulating back navigation | delay=%.1fs", back_delay
                        )
                        await asyncio.sleep(back_delay)

                    await _visit_page(link, depth + 1, page_url)

        await _visit_page(url, 1, None)

    result.success = result.pages_visited > 0
    log.info(
        "Browse complete | url=%s | total_bytes=%d | pages=%d | max_depth=%d",
        url, result.total_bytes, result.pages_visited, result.max_depth_reached,
    )
    return result


# ── Playwright backend ────────────────────────────────────────────────────────


async def browse_site_playwright(
    url: str,
    cfg: Config,
    on_page: BrowseCallback = None,
) -> BrowseResult:
    """Visit ``url`` using a real Chromium instance via Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.warning("Playwright not installed; falling back to aiohttp backend.")
        return await browse_site_aiohttp(url, cfg, on_page)

    result = BrowseResult(url=url)
    max_depth = max(1, min(3, cfg.browse_depth))
    links_per_page = max(1, min(3, cfg.browse_max_internal_links))
    visited: Set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=random.choice(_DESKTOP_UAS),
            viewport={
                "width": random.randint(1280, 1920),
                "height": random.randint(768, 1080),
            },
            locale=random.choice(["en-US", "en-GB"]),
            timezone_id="Europe/London",
            java_script_enabled=True,
            accept_downloads=False,
        )
        page = await ctx.new_page()

        log.info("Browsing | url=%s | backend=playwright | depth=%d", url, max_depth)

        async def _visit_page(
            page_url: str,
            depth: int,
            referer_url: Optional[str],
        ) -> None:
            """Recursively visit a page with human-like Playwright interactions."""
            if result.pages_visited >= _MAX_PAGES_PER_VISIT:
                return
            if page_url in visited:
                return

            visited.add(page_url)

            try:
                options = {"wait_until": "domcontentloaded", "timeout": 30_000}
                if referer_url:
                    options["referer"] = referer_url
                await page.goto(page_url, **options)

                # Random mouse movements before scrolling
                for _ in range(random.randint(2, 5)):
                    x = random.randint(100, 800)
                    y = random.randint(100, 500)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.5))

                # Simulate reading with initial pause
                await asyncio.sleep(random.uniform(1.5, 4.0))

                # Random scroll with varying speeds and distances
                scroll_iterations = random.randint(2, 6)
                for _ in range(scroll_iterations):
                    distance = random.randint(100, 800)
                    await page.mouse.wheel(0, distance)
                    # Variable scroll-pause to simulate reading
                    await asyncio.sleep(random.uniform(0.3, 2.0))

                content = await page.content()
                page_bytes = len(content.encode("utf-8", errors="replace"))
                result.total_bytes += page_bytes
                result.pages_visited += 1
                result.max_depth_reached = max(result.max_depth_reached, depth)

                title = await page.title() or _extract_title(content)
                log.info(
                    "Page loaded | url=%s | depth=%d | bytes=%d | title=%s",
                    page_url, depth, page_bytes, title[:60],
                )

                await _notify(on_page, page_url, title, depth)

                # Simulate reading time based on content length
                read_delay = _simulate_reading_delay(len(content))
                await asyncio.sleep(read_delay)

                # Follow internal links if depth allows
                if depth < max_depth and result.pages_visited < _MAX_PAGES_PER_VISIT:
                    links = _extract_internal_links(content, page_url, links_per_page)

                    for link in links:
                        if result.pages_visited >= _MAX_PAGES_PER_VISIT:
                            break

                        delay = random.uniform(*cfg.browse_delay_range)
                        delay *= random.uniform(0.7, 1.3)
                        await asyncio.sleep(delay)

                        # Random chance to go back first
                        if random.random() < 0.25 and referer_url:
                            await page.go_back()
                            await asyncio.sleep(random.uniform(1.0, 2.5))

                        # Try to click the link naturally instead of direct navigation
                        try:
                            link_elem = page.locator(f'a[href="{link}"]').first
                            if await link_elem.is_visible():
                                # Move mouse to the link before clicking
                                box = await link_elem.bounding_box()
                                if box:
                                    await page.mouse.move(
                                        box["x"] + box["width"] / 2,
                                        box["y"] + box["height"] / 2,
                                    )
                                    await asyncio.sleep(random.uniform(0.1, 0.3))
                                await link_elem.click()
                                await page.wait_for_load_state("domcontentloaded")

                                inner_content = await page.content()
                                inner_bytes = len(
                                    inner_content.encode("utf-8", errors="replace")
                                )
                                result.total_bytes += inner_bytes
                                result.pages_visited += 1
                                result.max_depth_reached = max(
                                    result.max_depth_reached, depth + 1
                                )
                                visited.add(link)

                                inner_title = await page.title() or _extract_title(
                                    inner_content
                                )
                                log.info(
                                    "Page loaded | url=%s | depth=%d | bytes=%d | title=%s",
                                    link, depth + 1, inner_bytes, inner_title[:60],
                                )
                                await _notify(on_page, link, inner_title, depth + 1)
                                await asyncio.sleep(_simulate_reading_delay(len(inner_content)))
                                continue
                        except Exception:
                            pass

                        # Fallback: direct navigation
                        await _visit_page(link, depth + 1, page_url)

            except Exception as exc:
                log.debug("Playwright nav error | url=%s | error=%s", page_url, exc)

        await _visit_page(url, 1, None)
        await browser.close()

    result.success = result.pages_visited > 0
    log.info(
        "Browse complete | url=%s | total_bytes=%d | pages=%d | max_depth=%d | backend=playwright",
        url, result.total_bytes, result.pages_visited, result.max_depth_reached,
    )
    return result


# ── Public entry point ────────────────────────────────────────────────────────


async def browse_site(
    url: str,
    cfg: Config,
    on_page: BrowseCallback = None,
) -> BrowseResult:
    """Browse a site using the configured backend."""
    if cfg.use_playwright:
        return await browse_site_playwright(url, cfg, on_page)
    return await browse_site_aiohttp(url, cfg, on_page)
