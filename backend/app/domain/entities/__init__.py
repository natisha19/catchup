"""Domain entities and value objects.

These are plain Python dataclasses — no SQLAlchemy, no Pydantic. They are the
language of the domain and the application layer. Infrastructure adapters map
to/from these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import (
    BaselineStatus,
    ChangeEventType,
    CorporateEventStatus,
    CorporateEventType,
    DataStatus,
    MarketStatus,
    ProviderStatus,
    SignificanceTier,
)


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    symbol: str
    company_name: str
    exchange: str
    currency: str
    provider_symbol: str | None = None
    sector: str | None = None


@dataclass(frozen=True)
class MarketSnapshot:
    instrument_id: str
    observed_at: datetime
    received_at: datetime | None
    price: float | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    currency: str
    source: str
    data_status: DataStatus
    id: int | None = None


@dataclass(frozen=True)
class CorporateEvent:
    instrument_id: str
    event_type: CorporateEventType
    event_time: datetime
    description: str
    source: str
    status: CorporateEventStatus
    raw_reference: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class ChangeSignal:
    instrument_id: str
    observed_at: datetime
    previous_snapshot_id: int | None
    current_snapshot_id: int | None
    event_type: ChangeEventType
    previous_price: float | None
    current_price: float | None
    return_pct: float | None
    baseline_mean: float | None
    baseline_std: float | None
    z_score: float | None
    current_volume: float | None
    baseline_average_volume: float | None
    volume_ratio: float | None
    significance: SignificanceTier
    reason_codes: list[str]
    data_status: DataStatus
    event_description: str
    id: int | None = None


@dataclass(frozen=True)
class UserLastSeen:
    user_id: str
    instrument_id: str
    last_seen_at: datetime
    last_seen_snapshot_id: int | None


@dataclass
class UserRelevance:
    summary: str
    top_reason_codes: list[str] = field(default_factory=list)


@dataclass
class CatchupFeed:
    last_checked_at: datetime | None
    market_status: MarketStatus
    last_market_session_at: datetime | None
    changes: list[ChangeSignal]
    unchanged_count: int
    provider_status: ProviderStatus
    user_relevance: UserRelevance | None
    # Exact snapshot watermark delivered in this response. Clients acknowledge
    # this value so a newer ingestion run cannot be accidentally marked read.
    acknowledgement: dict[str, int | None] = field(default_factory=dict)


@dataclass
class WatchlistItem:
    instrument: Instrument
    added_at: datetime
    baseline_status: BaselineStatus


@dataclass
class Watchlist:
    items: list[WatchlistItem]
    updated_at: datetime


@dataclass
class ChangeDetail:
    instrument: Instrument
    snapshot: MarketSnapshot | None
    previous_seen_price: float | None
    latest_signal: ChangeSignal | None
    other_signals: list[ChangeSignal]
    last_checked_note: str | None = None
    # Per-instrument exchange-calendar status (spec §16): the instrument's own
    # exchange (NSE/NASDAQ/NYSE), never the feed's global status.
    market_status: MarketStatus | None = None


@dataclass(frozen=True)
class ExploreItem:
    """A single instrument in an Explore section: real snapshot + latest signal."""

    instrument: Instrument
    snapshot: MarketSnapshot | None = None
    signal: ChangeSignal | None = None


@dataclass(frozen=True)
class ExploreSections:
    movers: list[ExploreItem]
    dippers: list[ExploreItem]
    unusual: list[ExploreItem]
    # Distinct sectors across the discovery universe (for by-sector browsing).
    sectors: list[str]
