"""
    network_service.py — Network interface discovery use-case service.

    Provides a list of available NICs for the settings UI.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.domain.interfaces import INetworkService


class NetworkService:
    """Application-level network interface management."""

    def __init__(self, network_service: INetworkService) -> None:
        self._network_service = network_service

    async def get_interfaces(self) -> List[Dict[str, Any]]:
        """Return all non-loopback network interfaces."""
        return await self._network_service.get_interfaces()
