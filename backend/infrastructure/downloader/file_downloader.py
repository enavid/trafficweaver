"""
    file_downloader.py — Async file downloader with throttling, random pauses,
    and resume-friendly chunk streaming.

    Downloads are discarded after completion since only the traffic
    generation effect is needed.
"""

from __future__ import annotations

import os
import time
import uuid
import random
import asyncio
import aiohttp
from typing import Optional

from backend.domain.entities import Config, DownloadResult
from backend.infrastructure.logging.log_handler import get_logger

log = get_logger("downloader")

_CHUNK_SIZE = 32 * 1024  # 32 KB chunks
_DOWNLOAD_DIR = "downloads"


def _random_ua() -> str:
    """Return a plausible desktop browser User-Agent string."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]
    return random.choice(agents)


async def _throttled_read(
    response: aiohttp.ClientResponse, speed_cap: int
) -> bytes:
    """Read the next chunk and sleep if we are above the speed cap."""
    chunk = await response.content.read(_CHUNK_SIZE)
    if chunk and speed_cap > 0:
        ideal_duration = len(chunk) / speed_cap
        await asyncio.sleep(ideal_duration)
    return chunk


async def download_file(
    url: str,
    cfg: Config,
    semaphore: asyncio.Semaphore,
) -> DownloadResult:
    """
    Download a remote file with throttling and random pauses.

    The downloaded file is discarded after completion since we only
    need the traffic generation effect.
    """
    result = DownloadResult(url=url)
    tmp_name = os.path.join(_DOWNLOAD_DIR, f"tmp_{uuid.uuid4().hex}")
    os.makedirs(_DOWNLOAD_DIR, exist_ok=True)

    timeout = aiohttp.ClientTimeout(total=None, connect=30)
    headers = {
        "User-Agent": _random_ua(),
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    async with semaphore:
        log.info("Download started | url=%s", url)
        start = time.monotonic()
        try:
            connector = (
                aiohttp.TCPConnector(local_addr=(cfg.bind_ip, 0))
                if cfg.bind_ip
                else None
            )
            async with aiohttp.ClientSession(
                connector=connector, headers=headers, timeout=timeout
            ) as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    with open(tmp_name, "wb") as fh:
                        paused = False
                        while True:
                            chunk = await _throttled_read(resp, cfg.download_speed_cap)
                            if not chunk:
                                break
                            fh.write(chunk)
                            result.bytes_downloaded += len(chunk)

                            # Random mid-download pause to simulate human behaviour
                            if (
                                not paused
                                and result.bytes_downloaded > 1 * 1024 ** 2
                                and random.random() < cfg.download_pause_probability
                            ):
                                pause_secs = random.randint(*cfg.download_pause_range)
                                log.debug(
                                    "Download paused | url=%s | pause_secs=%d",
                                    url,
                                    pause_secs,
                                )
                                paused = True
                                await asyncio.sleep(pause_secs)

            result.success = True
            result.duration_seconds = time.monotonic() - start
            avg_speed = result.bytes_downloaded / max(result.duration_seconds, 0.001)
            log.info(
                "Download complete | url=%s | bytes=%d | duration=%.1fs | avg_speed=%.1f KB/s",
                url,
                result.bytes_downloaded,
                result.duration_seconds,
                avg_speed / 1024,
            )
        except Exception as exc:
            result.error = str(exc)
            result.duration_seconds = time.monotonic() - start
            log.warning("Download failed | url=%s | error=%s", url, exc)
        finally:
            # Always clean up the temp file
            try:
                os.remove(tmp_name)
            except FileNotFoundError:
                pass

    return result
