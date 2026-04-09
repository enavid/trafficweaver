"""
    engine_routes.py — Engine control endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user, get_engine
from backend.application.engine_service import EngineService

router = APIRouter(tags=["Engine"])


# ── Request / Response models ─────────────────────────────────────────────────


class EngineStartRequest(BaseModel):
    """Parameters for starting the traffic engine."""

    total_days: int = Field(default=0, ge=0, description="Number of days to run (0 = forever)")


class EngineStatusResponse(BaseModel):
    """Current engine status."""

    running: bool
    current_day: int


class EngineMessageResponse(BaseModel):
    """Generic engine action response."""

    message: str


class CurrentBrowsingResponse(BaseModel):
    """Live browsing preview data."""

    url: str = ""
    title: str = ""
    depth: int = 0
    started_at: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/engine/status",
    response_model=EngineStatusResponse,
    summary="Get engine status",
    description="Return whether the engine is running and which day cycle it is on.",
)
async def engine_status(
    user: str = Depends(get_current_user),
    engine_svc: EngineService = Depends(get_engine),
) -> Dict[str, Any]:
    return engine_svc.get_status()


@router.post(
    "/engine/start",
    response_model=EngineMessageResponse,
    summary="Start engine",
    description="Start the traffic simulation engine.",
)
async def engine_start(
    req: EngineStartRequest,
    user: str = Depends(get_current_user),
    engine_svc: EngineService = Depends(get_engine),
) -> Dict[str, str]:
    try:
        return engine_svc.start(total_days=req.total_days)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/engine/stop",
    response_model=EngineMessageResponse,
    summary="Stop engine",
    description="Request a graceful engine shutdown.",
)
async def engine_stop(
    user: str = Depends(get_current_user),
    engine_svc: EngineService = Depends(get_engine),
) -> Dict[str, str]:
    try:
        return engine_svc.stop()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/engine/current-browsing",
    summary="Get current browsing state",
    description="Return the page currently being browsed by the engine (live preview).",
)
async def current_browsing(
    user: str = Depends(get_current_user),
    engine_svc: EngineService = Depends(get_engine),
) -> Optional[Dict[str, Any]]:
    return engine_svc.get_current_browsing()
