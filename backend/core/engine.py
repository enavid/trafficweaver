"""
    engine.py — Traffic simulation engine.

    Orchestrates file downloads and simulated browsing across 24 hours,
    respecting the human-activity schedule defined in config.
    Supports live-reload of configuration without restart.
    Integrates with the browse preview WebSocket and engine service
    for real-time dashboard updates.
"""

from __future__ import annotations

import time
import random
import asyncio
import threading
from datetime import datetime
from typing import List, Optional

from backend.domain.entities import BrowseUpdate, Config
from backend.infrastructure.config.toml_config import get_config_service
from backend.core.scheduler import generate_event_times, seconds_until
from backend.infrastructure.downloader.file_downloader import download_file
from backend.infrastructure.browser.browser_engine import browse_site
from backend.infrastructure.logging.log_handler import get_logger

log = get_logger("engine")


class TrafficEngine:
    """
    Manages the lifecycle of traffic simulation.

    The engine runs in a background asyncio loop and can be
    started / stopped / restarted from the API layer.
    """

    def __init__(self) -> None:
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = asyncio.Event()
        self._current_day: int = 0
        self._total_days: int = 0  # 0 = run forever

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_day(self) -> int:
        return self._current_day

    def start(self, total_days: int = 0) -> None:
        """Start the traffic engine in a background thread."""
        if self._running:
            log.warning("Engine already running; ignoring start request.")
            return

        self._total_days = total_days
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log.info("Engine started | total_days=%d (0=forever)", total_days)

    def stop(self) -> None:
        """Signal the engine to stop gracefully."""
        if not self._running:
            return
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        log.info("Engine stop requested.")

    def _run_loop(self) -> None:
        """Run the async event loop in a dedicated thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_loop())
        except Exception as exc:
            log.error("Engine crashed | error=%s", exc)
        finally:
            self._running = False
            self._loop.close()
            log.info("Engine thread exited.")

    async def _main_loop(self) -> None:
        """Main day-cycle loop."""
        self._stop_event = asyncio.Event()
        self._current_day = 0

        while self._running:
            self._current_day += 1
            log.info("Starting day cycle %d", self._current_day)

            try:
                await self._run_day()
            except asyncio.CancelledError:
                log.info("Day cycle cancelled.")
                break
            except Exception as exc:
                log.error("Day cycle failed | day=%d | error=%s", self._current_day, exc)

            if self._total_days > 0 and self._current_day >= self._total_days:
                log.info("Completed %d day(s). Engine finished.", self._total_days)
                break

            # Short gap between cycles
            log.info("Day %d complete. Waiting 60s before next cycle...", self._current_day)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60)
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue to next day

        self._running = False

    async def _run_day(self) -> None:
        """Execute a single 24-hour traffic simulation cycle."""
        cfg_svc = get_config_service()
        cfg = cfg_svc.get_config()

        # Lazy import to avoid circular dependencies
        from backend.infrastructure.persistence.sqlite_repository import SqliteRepository

        repo = SqliteRepository()
        await repo.initialize()

        try:
            # Randomise today's target +/- variance
            variance_factor = 1.0 + random.uniform(-cfg.daily_variance, cfg.daily_variance)
            todays_target = int(cfg.daily_target_bytes * variance_factor)

            log.info(
                "Day target | target=%.2f GB | variance=+/-%.0f%%",
                todays_target / 1024 ** 3,
                cfg.daily_variance * 100,
            )

            today = datetime.now().strftime("%Y-%m-%d")
            await repo.upsert_daily_stats(
                date=today,
                target_bytes=todays_target,
                started_at=time.time(),
                last_updated=time.time(),
            )

            # Load site lists from database
            download_sites = await repo.get_download_sites(enabled_only=True)
            browsing_sites = await repo.get_browsing_sites(enabled_only=True)

            if not download_sites and not browsing_sites:
                log.warning("No sites configured. Skipping day cycle.")
                return

            # Calculate event counts
            avg_file_size = (
                sum(s["size_bytes"] for s in download_sites) / len(download_sites)
                if download_sites
                else 100 * 1024 ** 2
            )
            n_file_events = (
                max(1, min(48, int(todays_target * 0.80 / max(avg_file_size, 1))))
                if download_sites
                else 0
            )
            n_browse_events = (
                max(1, min(100, int(todays_target * 0.20 / (500 * 1024))))
                if browsing_sites
                else 0
            )

            log.info(
                "Event plan | file_downloads=%d | browse_visits=%d",
                n_file_events,
                n_browse_events,
            )

            # Generate timestamps
            file_times = (
                generate_event_times(n_file_events, cfg.schedule_weights)
                if n_file_events
                else []
            )
            browse_times = (
                generate_event_times(n_browse_events, cfg.schedule_weights)
                if n_browse_events
                else []
            )

            # Run both streams concurrently
            semaphore = asyncio.Semaphore(cfg.max_concurrent_downloads)

            tasks = []
            if file_times:
                tasks.append(
                    self._run_file_downloads(cfg, today, semaphore, file_times, download_sites, repo)
                )
            if browse_times:
                tasks.append(
                    self._run_browsing(cfg, today, browse_times, browsing_sites, repo)
                )

            if tasks:
                await asyncio.gather(*tasks)

            stats = await repo.get_daily_stats(today)
            if stats:
                total = stats["downloaded_bytes"] + stats["browse_bytes"]
                pct = total / stats["target_bytes"] * 100 if stats["target_bytes"] else 0
                log.info(
                    "Day complete | total_bytes=%d | target=%d | progress=%.1f%%",
                    total,
                    stats["target_bytes"],
                    pct,
                )
        finally:
            await repo.close()

    async def _run_file_downloads(
        self,
        cfg: Config,
        today: str,
        semaphore: asyncio.Semaphore,
        event_times: List[datetime],
        sites: List[dict],
        repo,
    ) -> None:
        """Schedule and execute all file download events."""
        urls = [s["url"] for s in sites]
        random.shuffle(urls)
        scheduled_urls = (urls * ((len(event_times) // len(urls)) + 1))[
            : len(event_times)
        ]

        tasks = []
        for ts, url in zip(event_times, scheduled_urls):
            wait = seconds_until(ts)
            log.info(
                "File download scheduled | url=%s | in=%.0fs | at=%s",
                url,
                wait,
                ts.isoformat(),
            )

            async def _job(u=url, w=wait) -> None:
                if not self._running:
                    return
                if w > 0:
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=w)
                        return  # Stopped
                    except asyncio.TimeoutError:
                        pass

                # Reload config for live updates
                current_cfg = get_config_service().get_config()
                result = await download_file(u, current_cfg, semaphore)

                # Update stats in DB
                stats = await repo.get_daily_stats(today)
                if stats:
                    await repo.upsert_daily_stats(
                        date=today,
                        downloaded_bytes=stats["downloaded_bytes"]
                        + result.bytes_downloaded,
                        file_downloads_ok=stats["file_downloads_ok"]
                        + (1 if result.success else 0),
                        file_downloads_fail=stats["file_downloads_fail"]
                        + (0 if result.success else 1),
                        last_updated=time.time(),
                    )

            tasks.append(asyncio.create_task(_job()))

        await asyncio.gather(*tasks)

    async def _run_browsing(
        self,
        cfg: Config,
        today: str,
        event_times: List[datetime],
        sites: List[dict],
        repo,
    ) -> None:
        """Schedule and execute all browsing events."""
        urls = [s["url"] for s in sites]
        random.shuffle(urls)
        scheduled_urls = (urls * ((len(event_times) // len(urls)) + 1))[
            : len(event_times)
        ]

        # Set up the browse update callback for live preview
        async def _on_page(update: BrowseUpdate) -> None:
            try:
                from backend.api.routes.ws_routes import broadcast_browse_update
                from backend.api.dependencies import _engine_svc

                await broadcast_browse_update(update)
                if _engine_svc:
                    _engine_svc.update_current_browsing(update)
            except Exception:
                pass

        tasks = []
        for ts, url in zip(event_times, scheduled_urls):
            wait = seconds_until(ts)
            log.info(
                "Browse event scheduled | url=%s | in=%.0fs | at=%s",
                url,
                wait,
                ts.isoformat(),
            )

            async def _job(u=url, w=wait) -> None:
                if not self._running:
                    return
                if w > 0:
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=w)
                        return
                    except asyncio.TimeoutError:
                        pass

                current_cfg = get_config_service().get_config()
                result = await browse_site(u, current_cfg, on_page=_on_page)

                stats = await repo.get_daily_stats(today)
                if stats:
                    await repo.upsert_daily_stats(
                        date=today,
                        browse_bytes=stats["browse_bytes"] + result.total_bytes,
                        browse_visits=stats["browse_visits"] + 1,
                        last_updated=time.time(),
                    )

            tasks.append(asyncio.create_task(_job()))

        await asyncio.gather(*tasks)


# Singleton engine instance
_engine: Optional[TrafficEngine] = None


def get_engine() -> TrafficEngine:
    global _engine
    if _engine is None:
        _engine = TrafficEngine()
    return _engine
