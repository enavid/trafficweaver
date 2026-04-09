"""
    ws_routes.py — WebSocket endpoints for real-time log and browse preview streaming.
"""

from __future__ import annotations

import asyncio
import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.api.auth import verify_token
from backend.domain.entities import BrowseUpdate
from backend.infrastructure.logging.log_handler import register_ws_callback, get_logger

log = get_logger("ws")

router = APIRouter()

# ── Log WebSocket ─────────────────────────────────────────────────────────────

_log_ws_clients: List[WebSocket] = []


async def _broadcast_log(level: str, logger_name: str, message: str) -> None:
    """Send log entry to all connected WebSocket clients."""
    data = json.dumps({"level": level, "logger": logger_name, "message": message})
    disconnected = []
    for ws in _log_ws_clients:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _log_ws_clients.remove(ws)


def _sync_broadcast(level: str, logger_name: str, message: str) -> None:
    """Thread-safe bridge to the async broadcast."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast_log(level, logger_name, message))
        else:
            loop.run_until_complete(_broadcast_log(level, logger_name, message))
    except RuntimeError:
        pass


# Register the broadcast callback
register_ws_callback(_sync_broadcast)


@router.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket) -> None:
    """WebSocket endpoint for real-time log streaming (authenticated via query param)."""
    token = ws.query_params.get("token")
    if not token or verify_token(token) is None:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    _log_ws_clients.append(ws)
    log.debug("Log WebSocket client connected | total=%d", len(_log_ws_clients))

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _log_ws_clients:
            _log_ws_clients.remove(ws)
        log.debug("Log WebSocket client disconnected | total=%d", len(_log_ws_clients))


# ── Browse Preview WebSocket ──────────────────────────────────────────────────

_browse_ws_clients: List[WebSocket] = []


async def broadcast_browse_update(update: BrowseUpdate) -> None:
    """
    Broadcast a browsing update to all connected preview clients.

    This function is passed as the ``on_page`` callback to the browser engine.
    """
    data = json.dumps({
        "type": "browse_update",
        "url": update.url,
        "title": update.title,
        "depth": update.depth,
        "timestamp": update.timestamp,
    })
    disconnected = []
    for ws in _browse_ws_clients:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _browse_ws_clients.remove(ws)


@router.websocket("/ws/browse-preview")
async def websocket_browse_preview(ws: WebSocket) -> None:
    """WebSocket endpoint for live browsing preview (authenticated via query param)."""
    token = ws.query_params.get("token")
    if not token or verify_token(token) is None:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    _browse_ws_clients.append(ws)
    log.debug("Browse preview WebSocket client connected | total=%d", len(_browse_ws_clients))

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _browse_ws_clients:
            _browse_ws_clients.remove(ws)
        log.debug("Browse preview WebSocket client disconnected | total=%d", len(_browse_ws_clients))
