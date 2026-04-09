"""
    log_routes.py — System log endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.api.dependencies import get_current_user, get_logs
from backend.application.log_service import LogService

router = APIRouter(tags=["Logs"])


# ── Response models ───────────────────────────────────────────────────────────


class ClearLogsResponse(BaseModel):
    """Result of a clear-logs operation."""

    deleted: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/logs",
    summary="Get system logs",
    description="Retrieve system log entries with optional level filtering and pagination.",
)
async def get_log_entries(
    limit: int = Query(default=200, ge=1, le=5000, description="Max entries to return"),
    level: Optional[str] = Query(default=None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    user: str = Depends(get_current_user),
    log_svc: LogService = Depends(get_logs),
) -> List[Dict[str, Any]]:
    return await log_svc.get_logs(limit=limit, level=level, offset=offset)


@router.delete(
    "/logs",
    response_model=ClearLogsResponse,
    summary="Clear all logs",
    description="Delete all persisted system log entries.",
)
async def clear_log_entries(
    user: str = Depends(get_current_user),
    log_svc: LogService = Depends(get_logs),
) -> Dict[str, Any]:
    return await log_svc.clear_logs()
