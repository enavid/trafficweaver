"""
    database.py — Backward-compatible synchronous SQLite layer.

    This module retains the synchronous API used by the log handler
    (which runs inside a logging.Handler and cannot be async) and by
    legacy code paths.  For new async code, use
    ``backend.infrastructure.persistence.sqlite_repository.SqliteRepository``.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional


_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "trafficweaver.db"
)
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Return a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(os.path.abspath(_DB_PATH)), exist_ok=True)
        _local.conn = sqlite3.connect(
            os.path.abspath(_DB_PATH), check_same_thread=False
        )
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db() -> None:
    """Create all tables if they do not exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS download_sites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT    NOT NULL,
            size_bytes  INTEGER NOT NULL DEFAULT 0,
            enabled     INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS browsing_sites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT    NOT NULL,
            enabled     INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_stats (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            date                TEXT    NOT NULL UNIQUE,
            target_bytes        INTEGER NOT NULL DEFAULT 0,
            downloaded_bytes    INTEGER NOT NULL DEFAULT 0,
            browse_bytes        INTEGER NOT NULL DEFAULT 0,
            file_downloads_ok   INTEGER NOT NULL DEFAULT 0,
            file_downloads_fail INTEGER NOT NULL DEFAULT 0,
            browse_visits       INTEGER NOT NULL DEFAULT 0,
            started_at          REAL    NOT NULL DEFAULT 0,
            last_updated        REAL    NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS system_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT    NOT NULL DEFAULT (datetime('now')),
            level      TEXT    NOT NULL DEFAULT 'INFO',
            logger     TEXT    NOT NULL DEFAULT '',
            message    TEXT    NOT NULL DEFAULT ''
        );
    """)
    conn.commit()


# ── System Logs (sync — used by DatabaseLogHandler) ───────────────────────────


def insert_log(level: str, logger: str, message: str) -> None:
    """Insert a log entry synchronously (called from logging handler)."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO system_logs (timestamp, level, logger, message) "
        "VALUES (datetime('now'), ?, ?, ?)",
        (level, logger, message),
    )
    conn.commit()


def get_logs(
    limit: int = 200, level: Optional[str] = None, offset: int = 0
) -> List[Dict[str, Any]]:
    conn = _get_conn()
    sql = "SELECT * FROM system_logs"
    params: list = []
    if level:
        sql += " WHERE level = ?"
        params.append(level)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def clear_logs() -> int:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM system_logs")
    conn.commit()
    return cursor.rowcount


# ── Download Sites (kept for backward compat) ────────────────────────────────


def get_download_sites(enabled_only: bool = False) -> List[Dict[str, Any]]:
    conn = _get_conn()
    sql = "SELECT * FROM download_sites"
    if enabled_only:
        sql += " WHERE enabled = 1"
    sql += " ORDER BY id"
    return [dict(row) for row in conn.execute(sql).fetchall()]


def add_download_site(url: str, size_bytes: int = 0) -> Dict[str, Any]:
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO download_sites (url, size_bytes) VALUES (?, ?)",
        (url, size_bytes),
    )
    conn.commit()
    return dict(
        conn.execute(
            "SELECT * FROM download_sites WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    )


def update_download_site(site_id: int, **kwargs: Any) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    allowed = {"url", "size_bytes", "enabled"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return None
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [site_id]
    conn.execute(f"UPDATE download_sites SET {set_clause} WHERE id = ?", values)
    conn.commit()
    row = conn.execute(
        "SELECT * FROM download_sites WHERE id = ?", (site_id,)
    ).fetchone()
    return dict(row) if row else None


def delete_download_site(site_id: int) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM download_sites WHERE id = ?", (site_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── Browsing Sites ────────────────────────────────────────────────────────────


def get_browsing_sites(enabled_only: bool = False) -> List[Dict[str, Any]]:
    conn = _get_conn()
    sql = "SELECT * FROM browsing_sites"
    if enabled_only:
        sql += " WHERE enabled = 1"
    sql += " ORDER BY id"
    return [dict(row) for row in conn.execute(sql).fetchall()]


def add_browsing_site(url: str) -> Dict[str, Any]:
    conn = _get_conn()
    cursor = conn.execute("INSERT INTO browsing_sites (url) VALUES (?)", (url,))
    conn.commit()
    return dict(
        conn.execute(
            "SELECT * FROM browsing_sites WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    )


def update_browsing_site(site_id: int, **kwargs: Any) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    allowed = {"url", "enabled"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return None
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [site_id]
    conn.execute(f"UPDATE browsing_sites SET {set_clause} WHERE id = ?", values)
    conn.commit()
    row = conn.execute(
        "SELECT * FROM browsing_sites WHERE id = ?", (site_id,)
    ).fetchone()
    return dict(row) if row else None


def delete_browsing_site(site_id: int) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM browsing_sites WHERE id = ?", (site_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── Daily Stats ───────────────────────────────────────────────────────────────


def get_daily_stats(date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT * FROM daily_stats WHERE date = ?", (date,)
    ).fetchone()
    return dict(row) if row else None


def upsert_daily_stats(date: str, **kwargs: Any) -> Dict[str, Any]:
    conn = _get_conn()
    existing = get_daily_stats(date)
    if existing:
        allowed = {
            "target_bytes", "downloaded_bytes", "browse_bytes",
            "file_downloads_ok", "file_downloads_fail", "browse_visits",
            "started_at", "last_updated",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [date]
            conn.execute(
                f"UPDATE daily_stats SET {set_clause} WHERE date = ?", values
            )
            conn.commit()
    else:
        import time

        defaults = {
            "date": date,
            "target_bytes": kwargs.get("target_bytes", 0),
            "downloaded_bytes": kwargs.get("downloaded_bytes", 0),
            "browse_bytes": kwargs.get("browse_bytes", 0),
            "file_downloads_ok": kwargs.get("file_downloads_ok", 0),
            "file_downloads_fail": kwargs.get("file_downloads_fail", 0),
            "browse_visits": kwargs.get("browse_visits", 0),
            "started_at": kwargs.get("started_at", time.time()),
            "last_updated": kwargs.get("last_updated", time.time()),
        }
        cols = ", ".join(defaults.keys())
        placeholders = ", ".join("?" for _ in defaults)
        conn.execute(
            f"INSERT INTO daily_stats ({cols}) VALUES ({placeholders})",
            list(defaults.values()),
        )
        conn.commit()
    return get_daily_stats(date)


def get_stats_history(limit: int = 30) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
