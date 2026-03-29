"""
    main.py – TrafficWeaver entry point.

    Orchestrates file downloads and simulated browsing across 24 hours,
    respecting the human-activity schedule defined in .env.
"""

from __future__ import annotations

import sys
import random
import asyncio
from datetime import datetime
from typing import List

from src.config import load_config
from src.browser import browse_site
from src.downloader import download_file
from src.logger import setup_logger, get_logger
from src.scheduler import generate_event_times, seconds_until
from src.stats import load_or_create, record_file_download, record_browse


async def _run_file_downloads(cfg, stats, semaphore, event_times: List[datetime]) -> None:
    """Schedule all file-download events and await them in order."""
    if not cfg.file_downloads:
        return

    log = get_logger("main.downloads")
    # Shuffle the list so the same file isn't always first
    urls = [e.url for e in cfg.file_downloads]
    random.shuffle(urls)

    # If we have more events than files, cycle through the list
    scheduled_urls = (urls * ((len(event_times) // len(urls)) + 1))[: len(event_times)]

    tasks = []
    for ts, url in zip(event_times, scheduled_urls):
        wait = seconds_until(ts)
        log.info("File download scheduled | url=%s | in=%.0fs | at=%s", url, wait, ts.isoformat())

        async def _job(u=url, w=wait):
            if w > 0:
                await asyncio.sleep(w)
            result = await download_file(u, cfg, semaphore)
            record_file_download(stats, result.bytes_downloaded, result.success)

        tasks.append(asyncio.create_task(_job()))

    await asyncio.gather(*tasks)


async def _run_browsing(cfg, stats, event_times: List[datetime]) -> None:
    """Schedule all browsing events and await them in order."""
    if not cfg.browsing_sites:
        return

    log = get_logger("main.browsing")
    sites = cfg.browsing_sites[:]
    random.shuffle(sites)
    scheduled_sites = (sites * ((len(event_times) // len(sites)) + 1))[: len(event_times)]

    tasks = []
    for ts, url in zip(event_times, scheduled_sites):
        wait = seconds_until(ts)
        log.info("Browse event scheduled | url=%s | in=%.0fs | at=%s", url, wait, ts.isoformat())

        async def _job(u=url, w=wait):
            if w > 0:
                await asyncio.sleep(w)
            received = await browse_site(u, cfg)
            record_browse(stats, received)

        tasks.append(asyncio.create_task(_job()))

    await asyncio.gather(*tasks)


async def main() -> None:
    cfg = load_config()
    setup_logger(cfg.log_file, cfg.log_level)
    log = get_logger("main")

    # Randomise today's target ± variance
    variance_factor = 1.0 + random.uniform(-cfg.daily_variance, cfg.daily_variance)
    todays_target = int(cfg.daily_target_bytes * variance_factor)

    log.info(
        "TrafficWeaver starting | target=%.2f GB | variance=±%.0f%%",
        todays_target / 1024 ** 3,
        cfg.daily_variance * 100,
    )

    stats = load_or_create(todays_target)

    # ── Decide how many events of each type to schedule ──────────────────────
    # Rough split: 80% of bytes from file downloads, 20% from browsing.
    # File events: target_bytes ÷ average_file_size, clamped to [1, 48]
    avg_file_size = (
        sum(e.size for e in cfg.file_downloads) / len(cfg.file_downloads)
        if cfg.file_downloads
        else 100 * 1024 ** 2
    )
    n_file_events = max(1, min(48, int(todays_target * 0.80 / max(avg_file_size, 1))))
    n_browse_events = max(1, min(100, int(todays_target * 0.20 / (500 * 1024))))  # ~500 KB/visit

    log.info(
        "Event plan | file_downloads=%d | browse_visits=%d",
        n_file_events,
        n_browse_events,
    )

    # Generate timestamps
    file_times = generate_event_times(n_file_events, cfg.schedule_weights)
    browse_times = generate_event_times(n_browse_events, cfg.schedule_weights)

    # Run both streams concurrently
    semaphore = asyncio.Semaphore(cfg.max_concurrent_downloads)
    await asyncio.gather(
        _run_file_downloads(cfg, stats, semaphore, file_times),
        _run_browsing(cfg, stats, browse_times),
    )

    log.info(
        "Day complete | total_bytes=%d | target=%d | progress=%.1f%%",
        stats.total_bytes,
        stats.target_bytes,
        stats.progress_pct,
    )


if __name__ == "__main__":
    try:
        raw = input("How many days to run? (0 = run forever): ").strip()
        total_days = int(raw) if raw.isdigit() else 0
        day = 1
        while True:
            print(f"\n[TrafficWeaver] Starting day {day}...")
            asyncio.run(main())
            if total_days > 0 and day >= total_days:
                print(f"[TrafficWeaver] Completed {total_days} day(s). Exiting.")
                break
            day += 1
            time.sleep(60)  # 60s gap between cycles
    except KeyboardInterrupt:
        print("\n[TrafficWeaver] Interrupted by user.")
        sys.exit(0)
