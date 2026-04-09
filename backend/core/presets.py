"""
    presets.py — Curated site presets and human-behavior schedule helpers.

    Provides:
      - Website presets organized by category
      - Human-like schedule weight calculators based on timezone-aware
        active hours
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

# ── Website Presets ──────────────────────────────────────────────────────────
# Curated list of popular websites organized by category.
# Sensitive categories (government services, finance/crypto) have been removed.

IRANIAN_SITES: Dict[str, List[str]] = {
    "messaging": [
        "https://eitaa.com",
        "https://rubika.ir",
        "https://bale.ai",
        "https://soroushplus.com",
        "https://gap.im",
        "https://igap.net",
    ],
    "video_streaming": [
        "https://www.aparat.com",
        "https://www.namasha.com",
        "https://www.filimo.com",
        "https://www.telewebion.com",
        "https://www.namava.ir",
        "https://www.tamasha.com",
        "https://www.uptvs.com",
        "https://www.youtube.com",
        "https://www.twitch.tv",
        "https://www.netflix.com",
        "https://www.dailymotion.com",
        "https://vimeo.com",
    ],
    "news": [
        "https://www.isna.ir",
        "https://www.irna.ir",
        "https://www.farsnews.ir",
        "https://www.mehrnews.com",
        "https://www.tasnimnews.com",
        "https://www.khabaronline.ir",
        "https://www.tabnak.ir",
        "https://www.hamshahrionline.ir",
        "https://www.entekhab.ir",
        "https://www.mashreghnews.ir",
        "https://www.ilna.ir",
        "https://www.shahrekhabar.com",
        "https://www.bartarinha.ir",
        "https://www.khabarvarzeshi.com",
        "https://www.yjc.ir",
        "https://www.imna.ir",
        "https://www.ana.ir",
        "https://www.asriran.com",
        "https://www.donya-e-eqtesad.com",
        "https://www.eghtesadnews.com",
        "https://www.eghtesadonline.com",
    ],
    "sports": [
        "https://www.varzesh3.com",
        "https://www.khabarvarzeshi.com",
        "https://www.90tv.ir",
        "https://www.footballi.net",
        "https://www.persianfootball.com",
        "https://www.navad.net",
    ],
    "ecommerce": [
        "https://www.digikala.com",
        "https://torob.com",
        "https://divar.ir",
        "https://www.sheypoor.com",
        "https://www.snappfood.ir",
        "https://www.banimode.com",
        "https://www.emalls.ir",
        "https://www.basalam.com",
        "https://www.zanbil.ir",
        "https://www.snapp.taxi",
        "https://www.tapsi.ir",
        "https://www.alopeyk.com",
        "https://www.esam.ir",
        "https://www.niazerooz.com",
        "https://www.istgah.com",
        "https://www.khanoumi.com",
    ],
    "travel": [
        "https://www.alibaba.ir",
        "https://www.snapptrip.com",
        "https://www.flightio.com",
        "https://www.safarmarket.com",
        "https://www.jabama.com",
        "https://www.trip.ir",
        "https://www.eligasht.com",
        "https://www.flytoday.ir",
    ],
    "tech_education": [
        "https://www.zoomit.ir",
        "https://www.zoomg.ir",
        "https://www.faradars.org",
        "https://maktabkhooneh.org",
        "https://www.virgool.io",
        "https://www.ninisite.com",
        "https://www.namnak.com",
        "https://www.tebyan.net",
        "https://www.civilica.com",
        "https://www.sid.ir",
        "https://www.chetor.com",
        "https://quera.org",
        "https://www.ponisha.ir",
        "https://www.coursera.org",
        "https://www.udemy.com",
        "https://www.khanacademy.org",
        "https://www.edx.org",
        "https://www.codecademy.com",
        "https://leetcode.com",
        "https://stackoverflow.com",
        "https://github.com",
        "https://www.w3schools.com",
        "https://developer.mozilla.org",
        "https://docs.python.org",
    ],
    "ai_services": [
        "https://chat.openai.com",
        "https://gemini.google.com",
        "https://claude.ai",
        "https://www.perplexity.ai",
        "https://chatgpt.com",
        "https://copilot.microsoft.com",
        "https://bard.google.com",
        "https://hoshiar.ai",
        "https://www.gilas.io",
        "https://ai.meta.com",
    ],
    "cloud_hosting": [
        "https://www.arvancloud.ir",
        "https://www.abr.arvancloud.ir",
        "https://www.iranserver.com",
        "https://www.parspack.com",
        "https://www.netafraz.com",
        "https://www.asiatech.ir",
        "https://www.hostiran.net",
        "https://www.mizbanfa.net",
        "https://www.mihanwebhost.com",
        "https://www.talahost.com",
        "https://www.mobinnet.ir",
    ],
    "apps_downloads": [
        "https://cafebazaar.ir",
        "https://myket.ir",
        "https://www.sibapp.com",
        "https://www.soft98.ir",
        "https://www.yasdl.com",
        "https://www.downloadha.com",
        "https://www.p30download.ir",
        "https://www.sarzamindownload.com",
        "https://www.farsroid.com",
        "https://www.dlfox.com",
        "https://www.patoghu.com",
        "https://download.ir",
    ],
    "search_maps": [
        "https://gerdoo.me",
        "https://www.zarebin.ir",
        "https://neshan.org",
        "https://balad.ir",
        "https://www.abadis.ir",
        "https://fastdic.com",
        "https://www.rismoon.com",
    ],
    "books_media": [
        "https://www.fidibo.com",
        "https://taaghche.com",
        "https://navaar.ir",
        "https://www.music-fa.com",
        "https://www.upmusics.com",
        "https://iranseda.ir",
    ],
    "telecom_isp": [
        "https://www.irancell.ir",
        "https://www.mci.ir",
        "https://www.rightel.ir",
        "https://www.tci.ir",
        "https://www.shatel.ir",
    ],
    "upload_tools": [
        "https://picofile.com",
        "https://uupload.ir",
        "https://uploadboy.com",
        "https://uploadkon.ir",
    ],
    "blog_community": [
        "https://blogfa.com",
        "https://www.blog.ir",
        "https://blogsky.com",
        "https://www.rtl-theme.com",
        "https://www.mihanwp.com",
        "https://www.hamyarwp.com",
        "https://abzarwp.com",
        "https://www.irantalent.com",
        "https://www.jobinja.ir",
        "https://www.jobvision.ir",
    ],
}


def get_all_iranian_urls() -> List[str]:
    """Return all preset URLs as a flat list."""
    urls: List[str] = []
    for category_urls in IRANIAN_SITES.values():
        urls.extend(category_urls)
    return urls


def get_preset_count() -> int:
    """Total number of preset sites."""
    return sum(len(v) for v in IRANIAN_SITES.values())


def get_preset_categories() -> Dict[str, int]:
    """Return category names with their site counts."""
    return {k: len(v) for k, v in IRANIAN_SITES.items()}


# ── Human-Behavior Schedule Calculator ───────────────────────────────────────


def compute_schedule_weights(
    wake_hour: int = 8,
    sleep_hour: int = 24,
    timezone_offset: float = 3.5,
) -> List[float]:
    """
    Compute the 4 schedule bucket weights (6-hour windows in UTC)
    given a local-time active window.

    The human activity is modeled as a bell curve peaking mid-day
    with zero activity outside wake-sleep hours.

    Args:
        wake_hour:  Hour of day (local) when activity starts (0-23)
        sleep_hour: Hour of day (local) when activity ends (0-24, 24 = midnight)
        timezone_offset: UTC offset in hours (e.g. 3.5 for Asia/Tehran)

    Returns:
        List of 4 weights (summing to ~1.0) for buckets [00-06, 06-12, 12-18, 18-24] UTC
    """
    # Convert local hours to UTC
    wake_utc = (wake_hour - timezone_offset) % 24
    sleep_utc = (sleep_hour - timezone_offset) % 24

    # Generate per-hour activity weights using a gaussian centered on midday
    # of the active window
    if sleep_hour > wake_hour:
        active_hours = sleep_hour - wake_hour
    else:
        active_hours = 24 - wake_hour + sleep_hour

    midpoint_local = (wake_hour + active_hours / 2) % 24
    sigma = active_hours / 4  # 95% of activity within the active window

    hour_weights = [0.0] * 24
    for h in range(24):
        local_h = (h + timezone_offset) % 24
        # Distance from midpoint (circular)
        diff = min(abs(local_h - midpoint_local), 24 - abs(local_h - midpoint_local))
        weight = math.exp(-0.5 * (diff / max(sigma, 1)) ** 2)

        # Zero out activity outside the wake-sleep window
        if sleep_hour > wake_hour:
            if local_h < wake_hour or local_h >= sleep_hour:
                weight = 0.0
        else:
            # Wraps around midnight
            if wake_hour > local_h >= sleep_hour:
                weight = 0.0

        hour_weights[h] = weight

    # Aggregate into 4 x 6-hour UTC buckets
    buckets = [0.0] * 4
    for h in range(24):
        buckets[h // 6] += hour_weights[h]

    # Normalize to sum = 1.0
    total = sum(buckets) or 1.0
    return [round(b / total, 4) for b in buckets]


# ── Timezone presets ─────────────────────────────────────────────────────────

TIMEZONES: Dict[str, float] = {
    "Asia/Tehran": 3.5,
    "Asia/Dubai": 4.0,
    "Asia/Kabul": 4.5,
    "Asia/Kolkata": 5.5,
    "Asia/Shanghai": 8.0,
    "Asia/Tokyo": 9.0,
    "Europe/Istanbul": 3.0,
    "Europe/Moscow": 3.0,
    "Europe/Berlin": 1.0,
    "Europe/London": 0.0,
    "America/New_York": -5.0,
    "America/Chicago": -6.0,
    "America/Denver": -7.0,
    "America/Los_Angeles": -8.0,
    "UTC": 0.0,
}
