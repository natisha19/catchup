"""Baseline calculation.

A rolling N-day baseline of the instrument's historical daily returns. The
current observation is NEVER included in its own baseline, preventing
self-contamination of the anomaly measure.

Baseline sufficiency (spec §17-18):
- >= MIN_BASELINE_RETURNS      -> SUFFICIENT
- >= LIMITED_BASELINE_RETURNS  -> LIMITED
  (z_score may remain usable if std > 0)
- otherwise                    -> UNAVAILABLE
  (z_score = None, never invented)
"""

from __future__ import annotations

import math
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
    """Arithmetic mean."""
    if not values:
        return 0.0

    return sum(float(value) for value in values) / len(values)


def _std(values: list[float]) -> float:
    """Sample standard deviation.

    Uses an explicit floating-point calculation instead of
    statistics.stdev(), avoiding the Fraction/numerator issue encountered
    during serverless ingestion.
    """
    if len(values) < 2:
        return 0.0

    numeric_values = [float(value) for value in values]
    mean = sum(numeric_values) / len(numeric_values)

    variance = sum(
        (value - mean) ** 2
        for value in numeric_values
    ) / (len(numeric_values) - 1)

    return math.sqrt(variance)