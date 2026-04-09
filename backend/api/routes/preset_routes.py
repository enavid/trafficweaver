"""
    preset_routes.py — Site preset and schedule computation endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user, get_sites
from backend.application.site_service import SiteService
from backend.core.presets import (
    IRANIAN_SITES,
    TIMEZONES,
    get_preset_count,
    get_preset_categories,
    compute_schedule_weights,
)

router = APIRouter(tags=["Presets"])


# ── Request / Response models ─────────────────────────────────────────────────


class LoadPresetRequest(BaseModel):
    """Optionally filter preset loading by category."""

    categories: Optional[List[str]] = Field(
        default=None,
        description="Category names to load. None = all categories.",
    )


class ComputeScheduleRequest(BaseModel):
    """Parameters for computing human-like schedule weights."""

    wake_hour: int = Field(default=8, ge=0, le=23, description="Wake hour (local time)")
    sleep_hour: int = Field(default=24, ge=0, le=24, description="Sleep hour (local time, 24 = midnight)")
    timezone_offset: float = Field(default=3.5, description="UTC offset in hours")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/presets/iranian-sites",
    summary="Get site presets",
    description="Return all curated preset sites organized by category.",
)
async def get_iranian_presets(
    user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    return {
        "total": get_preset_count(),
        "categories": get_preset_categories(),
        "sites": IRANIAN_SITES,
    }


@router.post(
    "/presets/load-iranian",
    summary="Load preset sites",
    description="Add curated preset sites to the browsing sites list. Optionally filter by category.",
)
async def load_iranian_preset(
    req: LoadPresetRequest,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    return await site_svc.load_preset_sites(IRANIAN_SITES, req.categories)


@router.get(
    "/presets/timezones",
    summary="Get timezone presets",
    description="Return available timezone presets with their UTC offsets.",
)
async def get_timezones(
    user: str = Depends(get_current_user),
) -> Dict[str, float]:
    return TIMEZONES


@router.post(
    "/presets/compute-schedule",
    summary="Compute schedule weights",
    description="Compute 4 schedule-bucket weights from human-readable active hours.",
)
async def compute_schedule(
    req: ComputeScheduleRequest,
    user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    weights = compute_schedule_weights(req.wake_hour, req.sleep_hour, req.timezone_offset)
    return {"weights": weights}
