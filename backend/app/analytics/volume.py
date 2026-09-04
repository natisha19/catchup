"""Volume ratio calculation.

volume_ratio = current_volume / baseline_average_volume

Uses the previous window's average volume. If the denominator is zero or
unavailable, volume_ratio = None (no division by zero).
"""

from __future__ import annotations

import statistics


def volume_ratio(
    current_volume: float | None,
    baseline_average_volume: float | None,
) -> float | None:
    if current_volume is None or baseline_average_volume is None:
        return None
    if baseline_average_volume <= 0:
        return None
    return current_volume / baseline_average_volume


def average_volume(volumes: list[float]) -> float:
    """Mean of historical volumes (for baseline average volume)."""
    if not volumes:
        return 0.0
    return statistics.fmean(volumes)
