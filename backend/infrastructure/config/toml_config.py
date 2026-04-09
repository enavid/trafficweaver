"""
    toml_config.py — TOML-based configuration with live-reload support.

    Reads config.toml (falls back to config.default.toml) and exposes a
    reactive Config object that can be updated at runtime via the UI
    without restarting the engine.

    Uses asyncio.Lock for full async safety.
"""

from __future__ import annotations

import asyncio
import copy
import os
from typing import Any, Callable, Dict, List, Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from backend.domain.entities import Config
from backend.domain.interfaces import IConfigService


_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_CONFIG_PATH = os.path.join(_BASE_DIR, "config.toml")
_DEFAULT_PATH = os.path.join(_BASE_DIR, "config.default.toml")

# Whitelist of allowed config update keys (dot-notation matching TOML paths)
ALLOWED_CONFIG_KEYS = frozenset({
    "server.host",
    "server.port",
    "server.secret_key",
    "auth.username",
    "auth.password_hash",
    "traffic.daily_target_bytes",
    "traffic.daily_variance",
    "traffic.schedule.weights",
    "traffic.download.max_concurrent",
    "traffic.download.speed_cap_bps",
    "traffic.download.pause_probability",
    "traffic.download.pause_range",
    "traffic.browsing.delay_range",
    "traffic.browsing.max_internal_links",
    "traffic.browsing.browse_depth",
    "traffic.browsing.use_playwright",
    "network.bind_ip",
    "network.interface",
    "timezone.name",
    "timezone.offset",
    "logging.level",
    "logging.file",
})


class TomlConfigService(IConfigService):
    """
    Async-safe configuration manager backed by TOML files.

    Loads from TOML, supports runtime updates via ``update_config()``,
    and notifies subscribers when configuration changes.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._config = Config()
        self._listeners: List[Callable[[Config], None]] = []
        self._load_from_toml()

    def _load_from_toml(self) -> None:
        """Read TOML file and populate the Config dataclass."""
        path = _CONFIG_PATH if os.path.exists(_CONFIG_PATH) else _DEFAULT_PATH
        if not os.path.exists(path):
            return

        with open(path, "rb") as fh:
            data = tomllib.load(fh)

        self._apply_dict(data)

    def _apply_dict(self, data: Dict[str, Any]) -> None:
        """Map nested TOML dict to flat Config fields."""
        c = self._config

        server = data.get("server", {})
        c.server_host = server.get("host", c.server_host)
        c.server_port = server.get("port", c.server_port)
        c.secret_key = server.get("secret_key", c.secret_key)

        auth = data.get("auth", {})
        c.auth_username = auth.get("username", c.auth_username)
        c.auth_password_hash = auth.get("password_hash", c.auth_password_hash)

        traffic = data.get("traffic", {})
        c.daily_target_bytes = traffic.get("daily_target_bytes", c.daily_target_bytes)
        c.daily_variance = traffic.get("daily_variance", c.daily_variance)

        sched = traffic.get("schedule", {})
        c.schedule_weights = sched.get("weights", c.schedule_weights)

        dl = traffic.get("download", {})
        c.max_concurrent_downloads = dl.get("max_concurrent", c.max_concurrent_downloads)
        c.download_speed_cap = dl.get("speed_cap_bps", c.download_speed_cap)
        c.download_pause_probability = dl.get("pause_probability", c.download_pause_probability)
        pr = dl.get("pause_range", list(c.download_pause_range))
        c.download_pause_range = (pr[0], pr[1])

        br = traffic.get("browsing", {})
        dr = br.get("delay_range", list(c.browse_delay_range))
        c.browse_delay_range = (dr[0], dr[1])
        c.browse_max_internal_links = br.get("max_internal_links", c.browse_max_internal_links)
        c.browse_depth = br.get("browse_depth", c.browse_depth)
        c.use_playwright = br.get("use_playwright", c.use_playwright)

        net = data.get("network", {})
        bind_ip = net.get("bind_ip", "")
        c.bind_ip = bind_ip if bind_ip else None
        c.network_interface = net.get("interface", c.network_interface)

        tz = data.get("timezone", {})
        c.timezone = tz.get("name", c.timezone)
        c.timezone_offset = tz.get("offset", c.timezone_offset)

        log = data.get("logging", {})
        c.log_level = log.get("level", c.log_level)
        c.log_file = log.get("file", c.log_file)

    def get_config(self) -> Config:
        """Return a copy of the current configuration snapshot."""
        return copy.copy(self._config)

    # Keep a sync property for backward compatibility with code that reads .config
    @property
    def config(self) -> Config:
        return self.get_config()

    async def update_config(self, updates: Dict[str, Any]) -> Config:
        """
        Apply partial updates to the live config and persist to TOML.

        Keys use dot notation matching TOML paths, e.g.
        ``traffic.daily_target_bytes`` or ``traffic.download.speed_cap_bps``.
        Only whitelisted keys are accepted.
        """
        async with self._lock:
            c = self._config
            _map = {
                "server.host": ("server_host", str),
                "server.port": ("server_port", int),
                "server.secret_key": ("secret_key", str),
                "auth.username": ("auth_username", str),
                "auth.password_hash": ("auth_password_hash", str),
                "traffic.daily_target_bytes": ("daily_target_bytes", int),
                "traffic.daily_variance": ("daily_variance", float),
                "traffic.schedule.weights": ("schedule_weights", list),
                "traffic.download.max_concurrent": ("max_concurrent_downloads", int),
                "traffic.download.speed_cap_bps": ("download_speed_cap", int),
                "traffic.download.pause_probability": ("download_pause_probability", float),
                "traffic.download.pause_range": ("download_pause_range", tuple),
                "traffic.browsing.delay_range": ("browse_delay_range", tuple),
                "traffic.browsing.max_internal_links": ("browse_max_internal_links", int),
                "traffic.browsing.browse_depth": ("browse_depth", int),
                "traffic.browsing.use_playwright": ("use_playwright", bool),
                "network.bind_ip": ("bind_ip", str),
                "network.interface": ("network_interface", str),
                "timezone.name": ("timezone", str),
                "timezone.offset": ("timezone_offset", float),
                "logging.level": ("log_level", str),
                "logging.file": ("log_file", str),
            }

            for key, value in updates.items():
                if key not in ALLOWED_CONFIG_KEYS:
                    continue
                if key in _map:
                    attr, typ = _map[key]
                    if typ == tuple and isinstance(value, list):
                        value = tuple(value)
                    if attr == "bind_ip" and (value == "" or value is None):
                        value = None
                    setattr(c, attr, value)

            self._persist_toml()
            snapshot = copy.copy(c)

        # Notify listeners outside the lock
        for listener in self._listeners:
            try:
                listener(snapshot)
            except Exception:
                pass

        return snapshot

    def on_change(self, callback: Callable[[Config], None]) -> None:
        """Register a callback invoked whenever config is updated."""
        self._listeners.append(callback)

    def _persist_toml(self) -> None:
        """Write current config back to config.toml."""
        c = self._config
        lines = [
            "# TrafficWeaver Configuration (auto-generated)",
            "",
            "[server]",
            f'host = "{c.server_host}"',
            f"port = {c.server_port}",
            f'secret_key = "{c.secret_key}"',
            "",
            "[auth]",
            f'username = "{c.auth_username}"',
            f'password_hash = "{c.auth_password_hash}"',
            "",
            "[traffic]",
            f"daily_target_bytes = {c.daily_target_bytes}",
            f"daily_variance = {c.daily_variance}",
            "",
            "[traffic.schedule]",
            f"weights = {list(c.schedule_weights)}",
            "",
            "[traffic.download]",
            f"max_concurrent = {c.max_concurrent_downloads}",
            f"speed_cap_bps = {c.download_speed_cap}",
            f"pause_probability = {c.download_pause_probability}",
            f"pause_range = [{c.download_pause_range[0]}, {c.download_pause_range[1]}]",
            "",
            "[traffic.browsing]",
            f"delay_range = [{c.browse_delay_range[0]}, {c.browse_delay_range[1]}]",
            f"max_internal_links = {c.browse_max_internal_links}",
            f"browse_depth = {c.browse_depth}",
            f'use_playwright = {"true" if c.use_playwright else "false"}',
            "",
            "[network]",
            f'bind_ip = "{c.bind_ip or ""}"',
            f'interface = "{c.network_interface}"',
            "",
            "[timezone]",
            f'name = "{c.timezone}"',
            f"offset = {c.timezone_offset}",
            "",
            "[logging]",
            f'level = "{c.log_level}"',
            f'file = "{c.log_file}"',
            "",
        ]
        with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

    def to_dict(self) -> Dict[str, Any]:
        """Return the config as a nested dict matching the TOML structure."""
        c = self.get_config()
        return {
            "server": {
                "host": c.server_host,
                "port": c.server_port,
            },
            "traffic": {
                "daily_target_bytes": c.daily_target_bytes,
                "daily_variance": c.daily_variance,
                "schedule": {
                    "weights": list(c.schedule_weights),
                },
                "download": {
                    "max_concurrent": c.max_concurrent_downloads,
                    "speed_cap_bps": c.download_speed_cap,
                    "pause_probability": c.download_pause_probability,
                    "pause_range": list(c.download_pause_range),
                },
                "browsing": {
                    "delay_range": list(c.browse_delay_range),
                    "max_internal_links": c.browse_max_internal_links,
                    "browse_depth": c.browse_depth,
                    "use_playwright": c.use_playwright,
                },
            },
            "network": {
                "bind_ip": c.bind_ip or "",
                "interface": c.network_interface,
            },
            "timezone": {
                "name": c.timezone,
                "offset": c.timezone_offset,
            },
            "logging": {
                "level": c.log_level,
                "file": c.log_file,
            },
        }


# ── Singleton accessor ───────────────────────────────────────────────────────

_service: Optional[TomlConfigService] = None


def get_config_service() -> TomlConfigService:
    """Return the global TomlConfigService singleton."""
    global _service
    if _service is None:
        _service = TomlConfigService()
    return _service
