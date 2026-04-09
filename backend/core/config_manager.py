"""
    config_manager.py — Backward-compatible shim.

    Delegates to the new infrastructure config service.
    Existing code that imports ``get_config_manager`` or the ``Config``
    dataclass will continue to work.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from backend.domain.entities import Config  # noqa: F401 — re-export
from backend.infrastructure.config.toml_config import (
    TomlConfigService,
    get_config_service,
)


class ConfigManager:
    """
    Backward-compatible wrapper around TomlConfigService.

    Provides the same synchronous interface that existing code expects
    (``config`` property, ``update()``, ``on_change()``, ``to_dict()``).
    """

    def __init__(self) -> None:
        self._svc = get_config_service()

    @property
    def config(self) -> Config:
        return self._svc.get_config()

    def update(self, updates: Dict[str, Any]) -> Config:
        """Synchronous update — wraps the async method for legacy callers."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Schedule the coroutine on the running loop
            future = asyncio.ensure_future(self._svc.update_config(updates))
            # Return current config (update happens asynchronously)
            return self._svc.get_config()
        else:
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(self._svc.update_config(updates))
            finally:
                new_loop.close()

    def on_change(self, callback: Callable[[Config], None]) -> None:
        self._svc.on_change(callback)

    def to_dict(self) -> Dict[str, Any]:
        return self._svc.to_dict()


# Singleton instance
_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    global _manager
    if _manager is None:
        _manager = ConfigManager()
    return _manager
