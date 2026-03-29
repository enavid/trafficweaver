"""
    scheduler.py – Distribute N events across 24 hours following human-like activity patterns (low at night, peaks morning/evening).
"""

from __future__ import annotations

import random
from typing import List
from datetime import datetime, timedelta


def _weight_for_hour(hour: int, weights: List[float]) -> float:
    """Map an hour (0-23) to its bucket weight."""
    bucket = hour // 6          # 0→[0-6), 1→[6-12), 2→[12-18), 3→[18-24)
    return weights[bucket]


def generate_event_times(count: int, weights: List[float], base: datetime | None = None) -> List[datetime]:
    """
    Return `count` datetime objects spread across the next 24 hours.
    Events are denser during high-weight periods and sparse at night.
    A small random jitter (±0 – 4 min) is applied to every timestamp
    so that no two events fall at identical seconds.
    """
    if base is None:
        base = datetime.now()

    # Build a weighted pool: for each minute in the day record its weight
    minutes_in_day = 24 * 60
    minute_weights: List[float] = []
    for m in range(minutes_in_day):
        hour = m // 60
        minute_weights.append(_weight_for_hour(hour, weights))

    chosen_minutes = random.choices(
        population=range(minutes_in_day),
        weights=minute_weights,
        k=count,
    )

    events: List[datetime] = []
    for m in sorted(chosen_minutes):
        jitter_seconds = random.randint(-90, 90)
        ts = base + timedelta(minutes=m, seconds=jitter_seconds)
        events.append(ts)

    return events


def seconds_until(target: datetime) -> float:
    """Seconds remaining until `target`; 0 if already in the past."""
    delta = (target - datetime.now()).total_seconds()
    return max(0.0, delta)
