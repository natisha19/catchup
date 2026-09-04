"""Return calculations.

return_t = (P_t / P_(t-1)) - 1

For consecutive valid observations we always use percentage returns for anomaly
detection, never raw price differences.
"""

from __future__ import annotations


def percent_return(previous_price: float, current_price: float) -> float:
    """Percentage return between two prices: ((current/previous) - 1) * 100."""
    if previous_price <= 0:
        raise ValueError("previous_price must be > 0")
    if current_price < 0:
        raise ValueError("current_price must be >= 0")
    return ((current_price / previous_price) - 1) * 100


def series_percent_returns(prices: list[float | None]) -> list[float]:
    """Consecutive percentage returns for a sequence of (valid) prices."""
    valid: list[float] = [p for p in prices if p is not None and p > 0]
    returns: list[float] = []
    for i in range(1, len(valid)):
        returns.append(percent_return(valid[i - 1], valid[i]))
    return returns
