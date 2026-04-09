"""
    config_service.py — Configuration use-case service.

    Thin wrapper over the infrastructure config layer that validates
    update keys against a whitelist before persisting changes.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from backend.domain.entities import Config
from backend.infrastructure.config.toml_config import (
    ALLOWED_CONFIG_KEYS,
    TomlConfigService,
)
from backend.infrastructure.logging.log_handler import get_logger

log = get_logger("config")


class ConfigService:
    """Application-level configuration management."""

    def __init__(self, config_service: TomlConfigService) -> None:
        self._config_service = config_service

    def get_config(self) -> Config:
        """Return the current configuration snapshot."""
        return self._config_service.get_config()

    async def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and apply configuration updates.

        Only whitelisted keys are accepted. Returns the full updated
        config as a nested dict.
        """
        # Filter to whitelisted keys only
        safe_updates = {
            k: v for k, v in updates.items() if k in ALLOWED_CONFIG_KEYS
        }
        if not safe_updates:
            log.warning("Config update rejected — no valid keys | attempted=%s", list(updates.keys()))
            return self._config_service.to_dict()

        await self._config_service.update_config(safe_updates)
        log.info("Configuration updated | keys=%s", list(safe_updates.keys()))
        return self._config_service.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Return the current config as a nested dict."""
        return self._config_service.to_dict()

    def on_change(self, callback: Callable[[Config], None]) -> None:
        """Register a callback invoked whenever config changes."""
        self._config_service.on_change(callback)
