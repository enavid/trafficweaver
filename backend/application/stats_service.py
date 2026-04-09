"""
    stats_service.py — Statistics use-case service.

    Provides access to daily traffic statistics and historical data.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.domain.interfaces import IStatsRepository


class StatsService:
    """Application-level access to traffic statistics."""

    def __init__(self, repository: IStatsRepository) -> None:
        self._repo = repository

    async def get_today_stats(self) -> Dict[str, Any]:
        """Return today's traffic statistics or zero defaults."""
        stats = await self._repo.get_daily_stats()
        if stats is None:
            return {
                "date": None,
                "target_bytes": 0,
                "downloaded_bytes": 0,
                "browse_bytes": 0,
                "file_downloads_ok": 0,
                "file_downloads_fail": 0,
                "browse_visits": 0,
            }
        return stats

    async def get_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Return historical daily statistics."""
        return await self._repo.get_stats_history(limit=limit)
