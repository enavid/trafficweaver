"""
    browser.py — Backward-compatible shim.

    Delegates to the infrastructure browser engine.
    Existing code that imports ``browse_site`` from here will continue to work.
"""

from backend.infrastructure.browser.browser_engine import (  # noqa: F401
    browse_site,
    browse_site_aiohttp,
    browse_site_playwright,
)
