"""
    config.py – Load and validate all settings from the .env file.
"""

from __future__ import annotations

import os
import textwrap
from dotenv import load_dotenv
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


load_dotenv()


def _parse_multiline_list(raw: str) -> List[str]:
    """Return non-empty, stripped lines from a triple-quoted env value."""
    return [line.strip() for line in raw.strip().splitlines() if line.strip()]


def _parse_weights(raw: str) -> List[float]:
    parts = [float(x.strip()) for x in raw.split(",") if x.strip()]
    if len(parts) != 4:
        raise ValueError("SCHEDULE_WEIGHTS must have exactly 4 comma-separated values.")
    return parts


@dataclass
class FileDownloadEntry:
    url: str
    size: int  # bytes (hint only; actual size measured at runtime)


@dataclass
class Config:
    # Daily target
    daily_target_bytes: int
    daily_variance: float

    # Lists
    file_downloads: List[FileDownloadEntry]
    browsing_sites: List[str]

    # Schedule
    schedule_weights: List[float]  # [00-06, 06-12, 12-18, 18-24]

    # Download behaviour
    max_concurrent_downloads: int
    download_speed_cap: int          # bytes/sec; 0 = unlimited
    download_pause_probability: float
    download_pause_range: Tuple[int, int]  # seconds

    # Browsing behaviour
    browse_delay_range: Tuple[int, int]  # seconds
    browse_max_internal_links: int
    use_playwright: bool

    # Logging
    log_level: str
    log_file: str

    bind_ip: Optional[str] = None

    # derived
    download_dir: str = field(default="downloads")


def load_config() -> Config:
    bind_ip = os.getenv("BIND_IP", None) or None,

    def _int(key: str, default: int) -> int:
        return int(os.getenv(key, str(default)))

    def _float(key: str, default: float) -> float:
        return float(os.getenv(key, str(default)))

    def _bool(key: str, default: bool) -> bool:
        return os.getenv(key, str(default)).strip().lower() in ("true", "1", "yes")

    def _range(key: str, default: str) -> Tuple[int, int]:
        raw = os.getenv(key, default)
        lo, hi = (int(x.strip()) for x in raw.split(","))
        return lo, hi

    raw_files = os.getenv("FILE_DOWNLOAD_LIST", "")
    file_entries: List[FileDownloadEntry] = []
    for line in _parse_multiline_list(raw_files):
        if "|" in line:
            url, size_str = line.rsplit("|", 1)
            file_entries.append(FileDownloadEntry(url=url.strip(), size=int(size_str.strip())))
        else:
            file_entries.append(FileDownloadEntry(url=line, size=0))

    raw_sites = os.getenv("BROWSING_SITE_LIST", "")
    sites = _parse_multiline_list(raw_sites)

    return Config(
        daily_target_bytes=_int("DAILY_TARGET_BYTES", 10 * 1024 ** 3),
        daily_variance=_float("DAILY_VARIANCE", 0.20),
        file_downloads=file_entries,
        browsing_sites=sites,
        schedule_weights=_parse_weights(os.getenv("SCHEDULE_WEIGHTS", "0.05,0.30,0.35,0.30")),
        max_concurrent_downloads=_int("MAX_CONCURRENT_DOWNLOADS", 2),
        download_speed_cap=_int("DOWNLOAD_SPEED_CAP", 2 * 1024 ** 2),
        download_pause_probability=_float("DOWNLOAD_PAUSE_PROBABILITY", 0.3),
        download_pause_range=_range("DOWNLOAD_PAUSE_RANGE", "15,120"),
        browse_delay_range=_range("BROWSE_DELAY_RANGE", "8,75"),
        browse_max_internal_links=_int("BROWSE_MAX_INTERNAL_LINKS", 3),
        use_playwright=_bool("USE_PLAYWRIGHT", False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "logs/trafficweaver.log"),
    )
