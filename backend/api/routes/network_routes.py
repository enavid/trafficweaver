"""
    network_routes.py — Network interface discovery endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.dependencies import get_current_user, get_network
from backend.application.network_service import NetworkService

router = APIRouter(tags=["Network"])


# ── Response models ───────────────────────────────────────────────────────────


class NetworkInterfaceResponse(BaseModel):
    """A single network interface."""

    name: str
    ip: str
    is_up: bool
    description: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/network/interfaces",
    response_model=List[NetworkInterfaceResponse],
    summary="List network interfaces",
    description="Return all non-loopback network interfaces with their IP addresses and status.",
)
async def list_network_interfaces(
    user: str = Depends(get_current_user),
    network_svc: NetworkService = Depends(get_network),
) -> List[Dict[str, Any]]:
    return await network_svc.get_interfaces()
