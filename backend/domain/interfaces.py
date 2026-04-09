"""
    interfaces.py — Abstract base classes defining repository and service contracts.

    All concrete implementations live in the infrastructure layer
    and depend on these abstractions, never the reverse.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from backend.domain.entities import (
    BrowseUpdate,
    Config,
    DailyStats,
    LogEntry,
    NetworkInterface,
    Site,
)


# ── Repository interfaces ────────────────────────────────────────────────────


class ISiteRepository(ABC):
    """Persistence contract for download and browsing sites."""

    # Download sites
    @abstractmethod
    async def get_download_sites(
        self, enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def add_download_site(
        self, url: str, size_bytes: int = 0
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def update_download_site(
        self, site_id: int, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def delete_download_site(self, site_id: int) -> bool:
        ...

    # Browsing sites
    @abstractmethod
    async def get_browsing_sites(
        self, enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def add_browsing_site(self, url: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def update_browsing_site(
        self, site_id: int, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def delete_browsing_site(self, site_id: int) -> bool:
        ...


class IStatsRepository(ABC):
    """Persistence contract for daily traffic statistics."""

    @abstractmethod
    async def get_daily_stats(
        self, date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def upsert_daily_stats(self, date: str, **kwargs: Any) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def get_stats_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        ...


class ILogRepository(ABC):
    """Persistence contract for system log records."""

    @abstractmethod
    async def insert_log(self, level: str, logger: str, message: str) -> None:
        ...

    @abstractmethod
    async def get_logs(
        self,
        limit: int = 200,
        level: Optional[str] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def clear_logs(self) -> int:
        ...


# ── Service interfaces ───────────────────────────────────────────────────────


class IConfigService(ABC):
    """Contract for reading and updating application configuration."""

    @abstractmethod
    def get_config(self) -> Config:
        ...

    @abstractmethod
    async def update_config(self, updates: Dict[str, Any]) -> Config:
        ...

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def on_change(self, callback: Callable[[Config], None]) -> None:
        ...


class INetworkService(ABC):
    """Contract for network interface discovery."""

    @abstractmethod
    async def get_interfaces(self) -> List[Dict[str, Any]]:
        ...
