"""
    log_handler.py — Structured logging with rotating files, DB persistence,
    and real-time WebSocket broadcast.

    Log format follows syslog-style conventions:
        2026-04-09T12:00:00 | INFO     | trafficweaver.main | Engine started
"""

from __future__ import annotations

import os
import sys
import logging
import asyncio
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, List, Optional


_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"

# WebSocket broadcast callbacks (set by the API layer)
_ws_callbacks: List[Callable] = []


def register_ws_callback(callback: Callable) -> None:
    """Register a callback that receives (level, logger_name, message) for every log entry."""
    _ws_callbacks.append(callback)


class DatabaseLogHandler(logging.Handler):
    """Persist every log record into SQLite and broadcast to WebSocket clients."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from backend.db.database import insert_log

            msg = self.format(record)
            insert_log(
                level=record.levelname,
                logger=record.name,
                message=record.getMessage(),
            )
            # Broadcast to WebSocket listeners
            for cb in _ws_callbacks:
                try:
                    cb(record.levelname, record.name, msg)
                except Exception:
                    pass
        except Exception:
            pass


def setup_logger(
    log_file: str = "logs/trafficweaver.log", log_level: str = "INFO"
) -> logging.Logger:
    """Initialize the root trafficweaver logger with console, file, and DB handlers."""
    os.makedirs(
        os.path.dirname(log_file) if os.path.dirname(log_file) else ".",
        exist_ok=True,
    )

    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = logging.Formatter(fmt=_FMT, datefmt=_DATE_FMT)

    root = logging.getLogger("trafficweaver")
    # Remove existing handlers to prevent duplicates on reload
    root.handlers.clear()
    root.setLevel(level)

    # Console handler (stdout)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # Rotating file handler (10 MB x 5 files)
    fh = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 ** 2, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # Database + WebSocket handler
    db_handler = DatabaseLogHandler()
    db_handler.setFormatter(formatter)
    root.addHandler(db_handler)

    return root


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the trafficweaver namespace."""
    return logging.getLogger(f"trafficweaver.{name}")


def update_log_level(level: str) -> None:
    """Dynamically change the log level without restarting."""
    root = logging.getLogger("trafficweaver")
    new_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(new_level)
    for handler in root.handlers:
        handler.setLevel(new_level)
