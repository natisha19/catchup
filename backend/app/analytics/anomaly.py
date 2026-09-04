"""Z-score (anomaly) calculation.

z_score = (current_return - baseline_mean) / baseline_std

When baseline_std == 0, z_score = None (no division by zero, no invented value).
"""

from __future__ import annotations


def z_score(
    current_return_pct: float | None,
    baseline_mean_pct: float | None,
    baseline_std_pct: float | None,
) -> float | None:
    if current_return_pct is None or baseline_mean_pct is None or baseline_std_pct is None:
        return None
    if baseline_std_pct == 0:
        return None
    return (current_return_pct - baseline_mean_pct) / baseline_std_pct
