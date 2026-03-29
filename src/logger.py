"""
    logger.py – Structured logging setup (file + console, RFC 3339 timestamps).
"""

from __future__ import annotations

import os
import sys
import logging
from logging.handlers import RotatingFileHandler


_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"


def setup_logger(log_file: str, log_level: str) -> logging.Logger:
    os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else ".", exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = logging.Formatter(fmt=_FMT, datefmt=_DATE_FMT)

    root = logging.getLogger("trafficweaver")
    root.setLevel(level)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # Rotating file handler (10 MB × 5 files)
    fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 ** 2, backupCount=5, encoding="utf-8")
    fh.setFormatter(formatter)
    root.addHandler(fh)

    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"trafficweaver.{name}")
