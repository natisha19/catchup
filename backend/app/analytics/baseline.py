"""Baseline calculation.

A rolling N-day baseline of the instrument's historical daily returns. The
current observation is NEVER included in its own baseline, preventing
self-contamination of the anomaly measure.

Baseline sufficiency (spec §17-18):
- >= MIN_BASELINE_RETURNS      -> SUFFICIENT
- >= LIMITED_BASELINE_RETURNS  -> LIMITED    (z_score may remain usable if std>0)
- otherwise                    -> UNAVAILABLE (z_score = None, never invented)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from app.domain.enums import BaselineStatus


@dataclass(frozen=True)
class Baseline:
    status: BaselineStatus
    mean: float | None
    std: float | None
    sample_size: int


def compute_baseline(
    returns: list[float],
    *,
    min_returns: int,
    limited_returns: int,
) -> Baseline:
    """Build a baseline from historical returns.

    `returns` is the instrument's prior daily returns (does not include the
    current return). Returns mean/std as floats, or None when insufficient.
    """
    if len(returns) >= min_returns:
        return Baseline(
            status=BaselineStatus.SUFFICIENT,
            mean=_mean(returns),
            std=_std(returns),
            sample_size=len(returns),
        )
    if len(returns) >= limited_returns:
        return Baseline(
            status=BaselineStatus.LIMITED,
            mean=_mean(returns),
            std=_std(returns),
            sample_size=len(returns),
        )
    return Baseline(
        status=BaselineStatus.UNAVAILABLE,
        mean=None,
        std=None,
        sample_size=len(returns),
    )


def _mean(values: list[float]) -> float:
    return statistics.fmean(values)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)
