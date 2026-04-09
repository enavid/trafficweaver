"""
    engine_service.py — Engine control use-case service.

    Manages start/stop lifecycle and provides current browsing state
    for real-time dashboard display.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.domain.entities import BrowseUpdate
from backend.infrastructure.logging.log_handler import get_logger

log = get_logger("engine_service")


class EngineService:
    """
    Application-level engine control.

    Wraps the core TrafficEngine and maintains the current-browsing
    state for live preview.
    """

    def __init__(self) -> None:
        self._current_browsing: Optional[Dict[str, Any]] = None

    def get_status(self) -> Dict[str, Any]:
        """Return the engine's running status."""
        from backend.core.engine import get_engine

        engine = get_engine()
        return {
            "running": engine.is_running,
            "current_day": engine.current_day,
        }

    def start(self, total_days: int = 0) -> Dict[str, str]:
        """Start the traffic engine."""
        from backend.core.engine import get_engine

        engine = get_engine()
        if engine.is_running:
            raise RuntimeError("Engine is already running")
        engine.start(total_days=total_days)
        return {"message": "Engine started"}

    def stop(self) -> Dict[str, str]:
        """Stop the traffic engine."""
        from backend.core.engine import get_engine

        engine = get_engine()
        if not engine.is_running:
            raise RuntimeError("Engine is not running")
        engine.stop()
        return {"message": "Engine stop requested"}

    def update_current_browsing(self, update: BrowseUpdate) -> None:
        """Update the current browsing state from a browse notification."""
        self._current_browsing = {
            "url": update.url,
            "title": update.title,
            "depth": update.depth,
            "started_at": update.timestamp,
        }

    def get_current_browsing(self) -> Optional[Dict[str, Any]]:
        """Return the current browsing state for dashboard display."""
        return self._current_browsing

    def clear_current_browsing(self) -> None:
        """Clear the browsing state when a session ends."""
        self._current_browsing = None
