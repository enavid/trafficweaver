"""
    site_service.py — Site management use-case service.

    Handles CRUD operations, import/export, and preset loading for
    both download and browsing sites.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.domain.interfaces import ISiteRepository
from backend.infrastructure.logging.log_handler import get_logger

log = get_logger("sites")


class SiteService:
    """Application-level site management for download and browsing targets."""

    def __init__(self, repository: ISiteRepository) -> None:
        self._repo = repository

    # ── Download Sites ────────────────────────────────────────────────────

    async def get_download_sites(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return await self._repo.get_download_sites(enabled_only=enabled_only)

    async def add_download_site(self, url: str, size_bytes: int = 0) -> Dict[str, Any]:
        result = await self._repo.add_download_site(url=url, size_bytes=size_bytes)
        log.info("Download site added | url=%s | size=%d", url, size_bytes)
        return result

    async def update_download_site(
        self, site_id: int, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        return await self._repo.update_download_site(site_id, **kwargs)

    async def delete_download_site(self, site_id: int) -> bool:
        deleted = await self._repo.delete_download_site(site_id)
        if deleted:
            log.info("Download site deleted | id=%d", site_id)
        return deleted

    async def import_download_sites(self, urls: List[str]) -> Dict[str, int]:
        """Import multiple download URLs, skipping duplicates."""
        existing = {s["url"] for s in await self._repo.get_download_sites()}
        added = 0
        for url in urls:
            url = url.strip()
            if url and url not in existing:
                await self._repo.add_download_site(url)
                existing.add(url)
                added += 1
        log.info("Download sites imported | added=%d | total_input=%d", added, len(urls))
        return {"added": added, "total_input": len(urls)}

    async def export_download_sites(self) -> Dict[str, Any]:
        sites = await self._repo.get_download_sites()
        return {"sites": sites, "count": len(sites)}

    # ── Browsing Sites ────────────────────────────────────────────────────

    async def get_browsing_sites(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return await self._repo.get_browsing_sites(enabled_only=enabled_only)

    async def add_browsing_site(self, url: str) -> Dict[str, Any]:
        result = await self._repo.add_browsing_site(url=url)
        log.info("Browsing site added | url=%s", url)
        return result

    async def update_browsing_site(
        self, site_id: int, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        return await self._repo.update_browsing_site(site_id, **kwargs)

    async def delete_browsing_site(self, site_id: int) -> bool:
        deleted = await self._repo.delete_browsing_site(site_id)
        if deleted:
            log.info("Browsing site deleted | id=%d", site_id)
        return deleted

    async def import_browsing_sites(self, urls: List[str]) -> Dict[str, int]:
        """Import multiple browsing URLs, skipping duplicates."""
        existing = {s["url"] for s in await self._repo.get_browsing_sites()}
        added = 0
        for url in urls:
            url = url.strip()
            if url and url not in existing:
                await self._repo.add_browsing_site(url)
                existing.add(url)
                added += 1
        log.info("Browsing sites imported | added=%d | total_input=%d", added, len(urls))
        return {"added": added, "total_input": len(urls)}

    async def export_browsing_sites(self) -> Dict[str, Any]:
        sites = await self._repo.get_browsing_sites()
        return {"sites": sites, "count": len(sites)}

    # ── Presets ───────────────────────────────────────────────────────────

    async def load_preset_sites(
        self, preset_sites: Dict[str, List[str]], categories: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Load preset browsing sites, optionally filtered by category."""
        if categories:
            urls = []
            for cat in categories:
                urls.extend(preset_sites.get(cat, []))
        else:
            urls = []
            for category_urls in preset_sites.values():
                urls.extend(category_urls)

        existing = {s["url"] for s in await self._repo.get_browsing_sites()}
        added = 0
        for url in urls:
            if url not in existing:
                await self._repo.add_browsing_site(url)
                added += 1

        log.info("Preset loaded | added=%d | skipped=%d", added, len(urls) - added)
        return {"added": added, "skipped": len(urls) - added, "total": len(urls)}
