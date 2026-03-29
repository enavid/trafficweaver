"""
    downloader.py – Async file downloader with throttling, random pauses, resume-friendly chunk streaming.
"""

from __future__ import annotations


import os
import time
import uuid
import random
import asyncio
import aiohttp
from typing import Optional
from src.config import Config
from src.logger import get_logger
from dataclasses import dataclass

log = get_logger("downloader")

_CHUNK_SIZE = 32 * 1024  # 32 KB chunks


@dataclass
class DownloadResult:
    url: str
    bytes_downloaded: int = 0
    success: bool = False
    error: Optional[str] = None
    duration_seconds: float = 0.0


async def _throttled_read(response: aiohttp.ClientResponse, speed_cap: int) -> bytes:
    """Read the next chunk and sleep if we are above the speed cap."""
    chunk = await response.content.read(_CHUNK_SIZE)
    if chunk and speed_cap > 0:
        # Time it *should* take to transfer this chunk at the cap
        ideal_duration = len(chunk) / speed_cap
        await asyncio.sleep(ideal_duration)
    return chunk


async def download_file(url: str, cfg: Config, semaphore: asyncio.Semaphore) -> DownloadResult:
    """
    Download a remote file into cfg.download_dir.
    - Throttles to cfg.download_speed_cap bytes/sec.
    - Randomly pauses mid-download to simulate human behaviour.
    - Discards the file after download (we only want the traffic).
    """
    result = DownloadResult(url=url)
    tmp_name = os.path.join(cfg.download_dir, f"tmp_{uuid.uuid4().hex}")
    os.makedirs(cfg.download_dir, exist_ok=True)

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
            connector = aiohttp.TCPConnector(local_addr=(cfg.bind_ip, 0)) if cfg.bind_ip else None
            async with aiohttp.ClientSession(connector=connector, headers=headers, timeout=timeout) as session:
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

                            # Random mid-download pause
                            if (
                                not paused
                                and result.bytes_downloaded > 1 * 1024 ** 2  # after 1 MB
                                and random.random() < cfg.download_pause_probability
                            ):
                                pause_secs = random.randint(*cfg.download_pause_range)
                                log.debug(
                                    "Download paused | url=%s | pause_secs=%d", url, pause_secs
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
            # Always clean up the temp file – we only wanted the traffic
            try:
                os.remove(tmp_name)
            except FileNotFoundError:
                pass

    return result


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
