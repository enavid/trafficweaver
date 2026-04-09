"""
    entities.py — Pure domain data classes.

    These represent the core business objects of TrafficWeaver.
    They contain no framework dependencies and no I/O logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Site:
    """A tracked website (download or browsing target)."""

    id: int = 0
    url: str = ""
    enabled: bool = True
    size_bytes: int = 0  # Only relevant for download sites
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DailyStats:
    """Aggregated traffic statistics for a single day."""

    id: int = 0
    date: str = ""
    target_bytes: int = 0
    downloaded_bytes: int = 0
    browse_bytes: int = 0
    file_downloads_ok: int = 0
    file_downloads_fail: int = 0
    browse_visits: int = 0
    started_at: float = 0.0
    last_updated: float = 0.0


@dataclass
class LogEntry:
    """A single structured log record."""

    id: int = 0
    timestamp: str = ""
    level: str = "INFO"
    logger: str = ""
    message: str = ""


@dataclass
class DownloadResult:
    """Outcome of a single file download attempt."""

    url: str = ""
    bytes_downloaded: int = 0
    success: bool = False
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class BrowseResult:
    """Outcome of a single site browsing session."""

    url: str = ""
    total_bytes: int = 0
    pages_visited: int = 0
    max_depth_reached: int = 0
    success: bool = False
    error: Optional[str] = None


@dataclass
class NetworkInterface:
    """A system network interface."""

    name: str = ""
    ip: str = ""
    is_up: bool = False
    description: str = ""


@dataclass
class BrowseUpdate:
    """Real-time browsing progress notification."""

    url: str = ""
    title: str = ""
    depth: int = 0
    timestamp: str = ""


@dataclass
class Config:
    """Immutable snapshot of the current application configuration."""

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8099
    secret_key: str = "change-me-in-production"

    # Auth
    auth_username: str = "admin"
    auth_password_hash: str = ""

    # Traffic targets
    daily_target_bytes: int = 10 * 1024 ** 3
    daily_variance: float = 0.20

    # Schedule weights (4 x 6-hour buckets)
    schedule_weights: List[float] = field(
        default_factory=lambda: [0.05, 0.30, 0.35, 0.30]
    )

    # Download behaviour
    max_concurrent_downloads: int = 2
    download_speed_cap: int = 2 * 1024 ** 2
    download_pause_probability: float = 0.3
    download_pause_range: Tuple[int, int] = (15, 120)

    # Browsing behaviour
    browse_delay_range: Tuple[int, int] = (8, 75)
    browse_max_internal_links: int = 3
    browse_depth: int = 2
    use_playwright: bool = False

    # Network
    bind_ip: Optional[str] = None
    network_interface: str = ""

    # Timezone
    timezone: str = "Asia/Tehran"
    timezone_offset: float = 3.5

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trafficweaver.log"
