"""
    sqlite_repository.py — Async SQLite persistence layer using aiosqlite.

    Implements ISiteRepository, IStatsRepository, and ILogRepository.
    All operations are fully asynchronous and safe for concurrent access.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite

from backend.domain.interfaces import ILogRepository, ISiteRepository, IStatsRepository


_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "trafficweaver.db")
)


class SqliteRepository(ISiteRepository, IStatsRepository, ILogRepository):
    """
    Unified async SQLite repository.

    Manages a single aiosqlite connection with WAL mode
    for optimal concurrent read/write throughput.
    """

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self._db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Open the database connection and create tables if needed."""
        os.makedirs(os.path.dirname(os.path.abspath(self._db_path)), exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()

    async def close(self) -> None:
        """Close the database connection gracefully."""
        if self._db:
            await self._db.close()
            self._db = None

    async def _create_tables(self) -> None:
        """Create all required tables if they do not already exist."""
        assert self._db is not None
        await self._db.executescript("""
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
        await self._db.commit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _fetchone_dict(
        self, sql: str, params: tuple = ()
    ) -> Optional[Dict[str, Any]]:
        assert self._db is not None
        cursor = await self._db.execute(sql, params)
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def _fetchall_dict(
        self, sql: str, params: tuple = ()
    ) -> List[Dict[str, Any]]:
        assert self._db is not None
        cursor = await self._db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Download Sites ────────────────────────────────────────────────────────

    async def get_download_sites(
        self, enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM download_sites"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY id"
        return await self._fetchall_dict(sql)

    async def add_download_site(
        self, url: str, size_bytes: int = 0
    ) -> Dict[str, Any]:
        assert self._db is not None
        cursor = await self._db.execute(
            "INSERT INTO download_sites (url, size_bytes) VALUES (?, ?)",
            (url, size_bytes),
        )
        await self._db.commit()
        return await self._fetchone_dict(
            "SELECT * FROM download_sites WHERE id = ?", (cursor.lastrowid,)
        )  # type: ignore[return-value]

    async def update_download_site(
        self, site_id: int, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        assert self._db is not None
        allowed = {"url", "size_bytes", "enabled"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return None
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [site_id]
        await self._db.execute(
            f"UPDATE download_sites SET {set_clause} WHERE id = ?", values
        )
        await self._db.commit()
        return await self._fetchone_dict(
            "SELECT * FROM download_sites WHERE id = ?", (site_id,)
        )

    async def delete_download_site(self, site_id: int) -> bool:
        assert self._db is not None
        cursor = await self._db.execute(
            "DELETE FROM download_sites WHERE id = ?", (site_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    # ── Browsing Sites ────────────────────────────────────────────────────────

    async def get_browsing_sites(
        self, enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM browsing_sites"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY id"
        return await self._fetchall_dict(sql)

    async def add_browsing_site(self, url: str) -> Dict[str, Any]:
        assert self._db is not None
        cursor = await self._db.execute(
            "INSERT INTO browsing_sites (url) VALUES (?)", (url,)
        )
        await self._db.commit()
        return await self._fetchone_dict(
            "SELECT * FROM browsing_sites WHERE id = ?", (cursor.lastrowid,)
        )  # type: ignore[return-value]

    async def update_browsing_site(
        self, site_id: int, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        assert self._db is not None
        allowed = {"url", "enabled"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return None
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [site_id]
        await self._db.execute(
            f"UPDATE browsing_sites SET {set_clause} WHERE id = ?", values
        )
        await self._db.commit()
        return await self._fetchone_dict(
            "SELECT * FROM browsing_sites WHERE id = ?", (site_id,)
        )

    async def delete_browsing_site(self, site_id: int) -> bool:
        assert self._db is not None
        cursor = await self._db.execute(
            "DELETE FROM browsing_sites WHERE id = ?", (site_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    # ── Daily Stats ───────────────────────────────────────────────────────────

    async def get_daily_stats(
        self, date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        return await self._fetchone_dict(
            "SELECT * FROM daily_stats WHERE date = ?", (date,)
        )

    async def upsert_daily_stats(
        self, date: str, **kwargs: Any
    ) -> Dict[str, Any]:
        assert self._db is not None
        existing = await self.get_daily_stats(date)
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
                await self._db.execute(
                    f"UPDATE daily_stats SET {set_clause} WHERE date = ?", values
                )
                await self._db.commit()
        else:
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
            await self._db.execute(
                f"INSERT INTO daily_stats ({cols}) VALUES ({placeholders})",
                list(defaults.values()),
            )
            await self._db.commit()

        result = await self.get_daily_stats(date)
        assert result is not None
        return result

    async def get_stats_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        return await self._fetchall_dict(
            "SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?", (limit,)
        )

    # ── System Logs ───────────────────────────────────────────────────────────

    async def insert_log(self, level: str, logger: str, message: str) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO system_logs (timestamp, level, logger, message) "
            "VALUES (datetime('now'), ?, ?, ?)",
            (level, logger, message),
        )
        await self._db.commit()

    async def get_logs(
        self,
        limit: int = 200,
        level: Optional[str] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM system_logs"
        params: list = []
        if level:
            sql += " WHERE level = ?"
            params.append(level)
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return await self._fetchall_dict(sql, tuple(params))

    async def clear_logs(self) -> int:
        assert self._db is not None
        cursor = await self._db.execute("DELETE FROM system_logs")
        await self._db.commit()
        return cursor.rowcount
