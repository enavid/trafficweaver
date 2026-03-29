"""
stats.py – Track daily download progress and persist across restarts.
"""

from __future__ import annotations

import os
import time
import json
from datetime import datetime
from src.logger import get_logger
from dataclasses import asdict, dataclass


log = get_logger("stats")
_STATS_FILE = "../logs/daily_stats.json"


@dataclass
class DailyStats:
    date: str                     # YYYY-MM-DD
    target_bytes: int
    downloaded_bytes: int = 0
    browse_bytes: int = 0
    file_downloads_ok: int = 0
    file_downloads_fail: int = 0
    browse_visits: int = 0
    started_at: float = 0.0
    last_updated: float = 0.0

    @property
    def total_bytes(self) -> int:
        return self.downloaded_bytes + self.browse_bytes

    @property
    def progress_pct(self) -> float:
        if self.target_bytes == 0:
            return 0.0
        return self.total_bytes / self.target_bytes * 100


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load_or_create(target_bytes: int) -> DailyStats:
    today = _today()
    os.makedirs(os.path.dirname(_STATS_FILE), exist_ok=True)
    if os.path.exists(_STATS_FILE):
        try:
            with open(_STATS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("date") == today:
                return DailyStats(**data)
        except Exception as exc:
            log.warning("Failed to load existing stats | error=%s", exc)

    stats = DailyStats(date=today, target_bytes=target_bytes, started_at=time.time())
    _save(stats)
    return stats


def _save(stats: DailyStats) -> None:
    stats.last_updated = time.time()
    with open(_STATS_FILE, "w", encoding="utf-8") as fh:
        json.dump(asdict(stats), fh, indent=2)


def record_file_download(stats: DailyStats, bytes_downloaded: int, success: bool) -> None:
    stats.downloaded_bytes += bytes_downloaded
    if success:
        stats.file_downloads_ok += 1
    else:
        stats.file_downloads_fail += 1
    _save(stats)
    log.info(
        "Stats updated | type=file | progress=%.1f%% | total_bytes=%d / %d",
        stats.progress_pct,
        stats.total_bytes,
        stats.target_bytes,
    )


def record_browse(stats: DailyStats, bytes_received: int) -> None:
    stats.browse_bytes += bytes_received
    stats.browse_visits += 1
    _save(stats)
    log.info(
        "Stats updated | type=browse | visits=%d | progress=%.1f%%",
        stats.browse_visits,
        stats.progress_pct,
    )
