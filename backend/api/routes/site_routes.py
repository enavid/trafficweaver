"""
    site_routes.py — Download and browsing site management endpoints.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.api.dependencies import get_current_user, get_sites
from backend.application.site_service import SiteService

router = APIRouter()


# ── Validators ────────────────────────────────────────────────────────────────


def _validate_url(url: str) -> str:
    """Ensure URL starts with http:// or https:// and is not excessively long."""
    url = url.strip()
    if len(url) > 2048:
        raise ValueError("URL exceeds maximum length of 2048 characters")
    if not re.match(r"^https?://", url):
        raise ValueError("URL must start with http:// or https://")
    return url


def _sanitize_name(name: str) -> str:
    """Strip potentially dangerous characters from site names."""
    return re.sub(r"[<>\"';\\]", "", name).strip()[:256]


# ── Request / Response models ─────────────────────────────────────────────────


class DownloadSiteCreate(BaseModel):
    """Create a new download site."""

    url: str = Field(..., max_length=2048, description="Download URL")
    size_bytes: int = Field(default=0, ge=0, description="Expected file size in bytes")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_url(v)


class DownloadSiteUpdate(BaseModel):
    """Partial update for a download site."""

    url: Optional[str] = Field(default=None, max_length=2048)
    size_bytes: Optional[int] = Field(default=None, ge=0)
    enabled: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_url(v)
        return v


class BrowsingSiteCreate(BaseModel):
    """Create a new browsing site."""

    url: str = Field(..., max_length=2048, description="Website URL to browse")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_url(v)


class BrowsingSiteUpdate(BaseModel):
    """Partial update for a browsing site."""

    url: Optional[str] = Field(default=None, max_length=2048)
    enabled: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_url(v)
        return v


class ImportSitesRequest(BaseModel):
    """Bulk import of site URLs."""

    urls: List[str] = Field(..., max_length=500, description="List of URLs to import")

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        for url in v:
            _validate_url(url)
        return v


class MessageResponse(BaseModel):
    message: str


# ── Download Site Endpoints ───────────────────────────────────────────────────


@router.get(
    "/download-sites",
    tags=["Download Sites"],
    summary="List download sites",
    description="Return all configured download sites.",
)
async def list_download_sites(
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> List[Dict[str, Any]]:
    return await site_svc.get_download_sites()


@router.post(
    "/download-sites",
    tags=["Download Sites"],
    summary="Add download site",
    description="Add a new download site to the list.",
)
async def create_download_site(
    site: DownloadSiteCreate,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    return await site_svc.add_download_site(url=site.url, size_bytes=site.size_bytes)


@router.patch(
    "/download-sites/{site_id}",
    tags=["Download Sites"],
    summary="Update download site",
    description="Partially update a download site by ID.",
)
async def update_download_site_route(
    site_id: int,
    site: DownloadSiteUpdate,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    updates = site.model_dump(exclude_none=True)
    if "enabled" in updates:
        updates["enabled"] = 1 if updates["enabled"] else 0
    result = await site_svc.update_download_site(site_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return result


@router.delete(
    "/download-sites/{site_id}",
    tags=["Download Sites"],
    response_model=MessageResponse,
    summary="Delete download site",
    description="Remove a download site by ID.",
)
async def delete_download_site_route(
    site_id: int,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, str]:
    if not await site_svc.delete_download_site(site_id):
        raise HTTPException(status_code=404, detail="Site not found")
    return {"message": "Deleted"}


@router.post(
    "/download-sites/import",
    tags=["Download Sites"],
    summary="Import download sites",
    description="Bulk import download site URLs, skipping duplicates.",
)
async def import_download_sites(
    req: ImportSitesRequest,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    return await site_svc.import_download_sites(req.urls)


@router.get(
    "/download-sites/export",
    tags=["Download Sites"],
    summary="Export download sites",
    description="Export all download sites as a JSON list.",
)
async def export_download_sites(
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    return await site_svc.export_download_sites()


# ── Browsing Site Endpoints ───────────────────────────────────────────────────


@router.get(
    "/browsing-sites",
    tags=["Browsing Sites"],
    summary="List browsing sites",
    description="Return all configured browsing sites.",
)
async def list_browsing_sites(
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> List[Dict[str, Any]]:
    return await site_svc.get_browsing_sites()


@router.post(
    "/browsing-sites",
    tags=["Browsing Sites"],
    summary="Add browsing site",
    description="Add a new browsing site to the list.",
)
async def create_browsing_site(
    site: BrowsingSiteCreate,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    return await site_svc.add_browsing_site(url=site.url)


@router.patch(
    "/browsing-sites/{site_id}",
    tags=["Browsing Sites"],
    summary="Update browsing site",
    description="Partially update a browsing site by ID.",
)
async def update_browsing_site_route(
    site_id: int,
    site: BrowsingSiteUpdate,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    updates = site.model_dump(exclude_none=True)
    if "enabled" in updates:
        updates["enabled"] = 1 if updates["enabled"] else 0
    result = await site_svc.update_browsing_site(site_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return result


@router.delete(
    "/browsing-sites/{site_id}",
    tags=["Browsing Sites"],
    response_model=MessageResponse,
    summary="Delete browsing site",
    description="Remove a browsing site by ID.",
)
async def delete_browsing_site_route(
    site_id: int,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, str]:
    if not await site_svc.delete_browsing_site(site_id):
        raise HTTPException(status_code=404, detail="Site not found")
    return {"message": "Deleted"}


@router.post(
    "/browsing-sites/import",
    tags=["Browsing Sites"],
    summary="Import browsing sites",
    description="Bulk import browsing site URLs, skipping duplicates.",
)
async def import_browsing_sites(
    req: ImportSitesRequest,
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    return await site_svc.import_browsing_sites(req.urls)


@router.get(
    "/browsing-sites/export",
    tags=["Browsing Sites"],
    summary="Export browsing sites",
    description="Export all browsing sites as a JSON list.",
)
async def export_browsing_sites(
    user: str = Depends(get_current_user),
    site_svc: SiteService = Depends(get_sites),
) -> Dict[str, Any]:
    return await site_svc.export_browsing_sites()
