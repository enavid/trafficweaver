"""
    psutil_network.py — Cross-platform network interface discovery using psutil.

    Implements INetworkService to enumerate NICs on Windows and Linux,
    filtering out loopback interfaces.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import psutil

from backend.domain.interfaces import INetworkService


class PsutilNetworkService(INetworkService):
    """Discover available network interfaces via psutil."""

    async def get_interfaces(self) -> List[Dict[str, Any]]:
        """
        Return a list of non-loopback network interfaces.

        Each entry contains:
            - name:        interface identifier (e.g. ``eth0``, ``Wi-Fi``)
            - ip:          first IPv4 address or empty string
            - is_up:       whether the interface link is active
            - description: human-readable description
        """
        # Run psutil calls in a thread to avoid blocking the event loop
        return await asyncio.to_thread(self._collect_interfaces)

    @staticmethod
    def _collect_interfaces() -> List[Dict[str, Any]]:
        """Synchronous NIC collection (offloaded to a thread)."""
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        interfaces: List[Dict[str, Any]] = []

        for name, addr_list in addrs.items():
            # Skip loopback interfaces
            if name.lower() in ("lo", "loopback", "lo0"):
                continue

            ipv4 = ""
            is_loopback = False
            for snic in addr_list:
                if snic.family.name == "AF_INET":
                    ipv4 = snic.address
                    if ipv4.startswith("127."):
                        is_loopback = True
                        break

            if is_loopback:
                continue

            nic_stats = stats.get(name)
            is_up = nic_stats.isup if nic_stats else False

            # Build a description from the NIC name
            description = _describe_nic(name)

            interfaces.append({
                "name": name,
                "ip": ipv4,
                "is_up": is_up,
                "description": description,
            })

        return interfaces


def _describe_nic(name: str) -> str:
    """Generate a human-readable description for a network interface name."""
    lower = name.lower()
    if "eth" in lower:
        return "Ethernet"
    if "wlan" in lower or "wi-fi" in lower or "wifi" in lower or "wireless" in lower:
        return "Wi-Fi"
    if "docker" in lower:
        return "Docker Bridge"
    if "veth" in lower:
        return "Virtual Ethernet"
    if "vmnet" in lower or "vmware" in lower:
        return "VMware Network"
    if "vbox" in lower or "virtualbox" in lower:
        return "VirtualBox Network"
    if "tun" in lower or "tap" in lower:
        return "VPN Tunnel"
    if "br" in lower and "bridge" not in lower:
        return "Bridge"
    if "bond" in lower:
        return "Bonded Interface"
    if "wg" in lower:
        return "WireGuard"
    if "bluetooth" in lower or "bnep" in lower:
        return "Bluetooth"
    # Windows-style names
    if "ethernet" in lower:
        return "Ethernet"
    if "local area connection" in lower:
        return "Ethernet"
    return name
