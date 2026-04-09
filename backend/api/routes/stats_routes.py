"""
    stats_routes.py — Traffic statistics endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.api.dependencies import get_current_user, get_stats
from backend.application.stats_service import StatsService

router = APIRouter(tags=["Statistics"])


# ── Response models ───────────────────────────────────────────────────────────


class DailyStatsResponse(BaseModel):
    """Today's traffic statistics."""

    class Config:
        extra = "allow"


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/stats/today",
    summary="Get today's statistics",
    description="Return aggregated traffic statistics for the current day.",
)
async def get_today_stats(
    user: str = Depends(get_current_user),
    stats_svc: StatsService = Depends(get_stats),
) -> Dict[str, Any]:
    return await stats_svc.get_today_stats()


@router.get(
    "/stats/history",
    summary="Get statistics history",
    description="Return historical daily statistics. Default limit is 30 days.",
)
async def get_stats_history(
    limit: int = Query(default=30, ge=1, le=365, description="Number of days to retrieve"),
    user: str = Depends(get_current_user),
    stats_svc: StatsService = Depends(get_stats),
) -> List[Dict[str, Any]]:
    return await stats_svc.get_history(limit=limit)
