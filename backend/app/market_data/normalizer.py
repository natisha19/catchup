"""Normalizer.

Translates normalized provider candidates into validated domain MarketSnapshot
objects. Separating validation (pure well-formedness) from normalization
(assigning identity/status/source) keeps each concern small.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.entities import MarketSnapshot
from app.domain.enums import DataStatus
from app.market_data.data_types import MarketSnapshotCandidate
from app.market_data.validator import validate_candidate


def normalize_snapshot(
    instrument_id: str,
    candidate: MarketSnapshotCandidate,
    source: str,
    received_at: datetime | None = None,
    data_status: DataStatus = DataStatus.LIVE,
) -> MarketSnapshot:
    """Validate a candidate and produce a stored MarketSnapshot domain object."""
    validated = validate_candidate(candidate)
    return MarketSnapshot(
        instrument_id=instrument_id,
        observed_at=_ensure_aware(validated.observed_at),
        received_at=_ensure_aware(received_at or datetime.now(timezone.utc)),
        price=validated.price,
        open=validated.open,
        high=validated.high,
        low=validated.low,
        close=validated.close,
        volume=validated.volume,
        currency=validated.currency,
        source=source,
        data_status=data_status,
    )


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
