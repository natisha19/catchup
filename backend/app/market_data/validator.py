"""Market data validation.

Pure functions that decide whether an observation is well-formed and
internally consistent. Invalid observations are rejected before persistence —
we never generate anomaly signals from invalid data.
"""

from __future__ import annotations

from app.market_data.data_types import MarketSnapshotCandidate


class InvalidObservation(ValueError):
    """Raised when an observation fails validation."""


def validate_candidate(candidate: MarketSnapshotCandidate) -> MarketSnapshotCandidate:
    """Validate a raw observation; raises InvalidObservation if malformed."""
    errors: list[str] = []

    if candidate.price is not None and not (candidate.price > 0):
        errors.append("price must be > 0")

    if candidate.open is not None and not (candidate.open > 0):
        errors.append("open must be > 0")
    if candidate.high is not None and not (candidate.high > 0):
        errors.append("high must be > 0")
    if candidate.low is not None and not (candidate.low > 0):
        errors.append("low must be > 0")
    if candidate.close is not None and not (candidate.close > 0):
        errors.append("close must be > 0")

    for name, val in (("price", candidate.price), ("open", candidate.open),
                      ("high", candidate.high), ("low", candidate.low),
                      ("close", candidate.close)):
        if val is not None and val < 0:
            errors.append(f"{name} must be >= 0")

    if candidate.volume is not None and candidate.volume < 0:
        errors.append("volume must be >= 0")

    # High/low OHLC consistency.
    if candidate.low is not None and candidate.high is not None and candidate.low > candidate.high:
        errors.append("low must be <= high")
    if candidate.low is not None and candidate.open is not None and candidate.low > candidate.open:
        errors.append("low must be <= open")
    if candidate.low is not None and candidate.close is not None and candidate.low > candidate.close:
        errors.append("low must be <= close")
    if candidate.high is not None and candidate.open is not None and candidate.open > candidate.high:
        errors.append("open must be <= high")
    if candidate.high is not None and candidate.close is not None and candidate.close > candidate.high:
        errors.append("close must be <= high")

    if errors:
        raise InvalidObservation("; ".join(errors))

    return candidate
