"""Market clock.

Determines marketStatus separately from dataStatus.

Key rule (spec §26, §60): "market closed" is NOT the same as "data unavailable."
A recent observation means the market is open/live; an older-but-valid
observation from a completed session is still valid historical market state.

For v1 this uses a simple, deterministic heuristic based on observation recency
relative to a stale threshold. It is intentionally replaceable so a proper
exchange-calendar implementation can be introduced later.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.enums import MarketStatus


def market_status(
    latest_observed_at: datetime | None,
    *,
    now: datetime | None = None,
    stale_threshold_minutes: int,
) -> MarketStatus:
    if latest_observed_at is None:
        return MarketStatus.UNKNOWN
    now = now or datetime.now(timezone.utc)
    latest = _aware(latest_observed_at)
    threshold = timedelta(minutes=stale_threshold_minutes)

    if now - latest <= threshold:
        # A recent observation implies the market is (or was just) open.
        return MarketStatus.OPEN
    # Older observation => last completed session is still the valid state.
    return MarketStatus.CLOSED


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
