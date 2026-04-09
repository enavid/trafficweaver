"""
    downloader.py — Backward-compatible shim.

    Delegates to the infrastructure file downloader.
"""

from backend.infrastructure.downloader.file_downloader import (  # noqa: F401
    DownloadResult,
    download_file,
)
