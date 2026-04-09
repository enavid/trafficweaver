"""
    log_service.py — Log management use-case service.

    Provides access to persisted log entries with filtering and clearing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.domain.interfaces import ILogRepository


class LogService:
    """Application-level log management."""

    def __init__(self, repository: ILogRepository) -> None:
        self._repo = repository

    async def get_logs(
        self,
        limit: int = 200,
        level: Optional[str] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Retrieve log entries with optional level filter."""
        return await self._repo.get_logs(limit=limit, level=level, offset=offset)

    async def clear_logs(self) -> Dict[str, int]:
        """Delete all persisted log entries. Returns deleted count."""
        count = await self._repo.clear_logs()
        return {"deleted": count}
