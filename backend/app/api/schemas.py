"""API schemas (Pydantic).

Separate from SQLAlchemy ORM models and domain dataclasses. These are the
public wire contract the frontend depends on, so the JSON field names mirror
the existing React types exactly (camelCase).

Field names here are snake_case (what the mapper construction uses); each field
declares a camelCase alias so FastAPI's serialization (by_alias=True by default)
emits the camelCase contract the frontend expects. `populate_by_name` lets the
mappers pass snake_case keywords while still accepting camelCase on input.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_alias = ConfigDict(populate_by_name=True)


# --------------------------------------------------------------------------- #
# Shared
# --------------------------------------------------------------------------- #
class InstrumentOut(BaseModel):
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    company_name: str = Field(alias="companyName")
    exchange: str
    currency: str
    sector: str | None = None

    model_config = _alias


class ChangeSignalOut(BaseModel):
    id: str
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    company_name: str = Field(alias="companyName")
    previous_price: float | None = Field(alias="previousPrice")
    current_price: float | None = Field(alias="currentPrice")
    return_pct: float | None = Field(alias="returnPct")
    baseline_mean: float | None = Field(alias="baselineMean")
    baseline_std: float | None = Field(alias="baselineStd")
    z_score: float | None = Field(alias="zScore")
    current_volume: float | None = Field(alias="currentVolume")
    baseline_average_volume: float | None = Field(alias="baselineAverageVolume")
    volume_ratio: float | None = Field(alias="volumeRatio")
    event_type: str = Field(alias="eventType")
    reason_codes: list[str] = Field(alias="reasonCodes")
    event_description: str = Field(alias="eventDescription")
    significance: str
    observed_at: datetime = Field(alias="observedAt")
    data_status: str = Field(alias="dataStatus")

    model_config = _alias


class MarketSnapshotOut(BaseModel):
    instrument_id: str = Field(alias="instrumentId")
    observed_at: datetime = Field(alias="observedAt")
    received_at: datetime | None = Field(alias="receivedAt")
    price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    source: str
    data_status: str = Field(alias="dataStatus")

    model_config = _alias


# --------------------------------------------------------------------------- #
# Catchup
# --------------------------------------------------------------------------- #
class UserRelevanceOut(BaseModel):
    summary: str
    top_reason_codes: list[str] = Field(alias="topReasonCodes")

    model_config = _alias


class CatchupFeedOut(BaseModel):
    last_checked_at: datetime | None = Field(alias="lastCheckedAt", default=None)
    market_status: str = Field(alias="marketStatus")
    last_market_session_at: datetime | None = Field(alias="lastMarketSessionAt", default=None)
    changes: list[ChangeSignalOut]
    unchanged_count: int = Field(alias="unchangedCount")
    provider_status: str | None = Field(alias="providerStatus", default=None)
    user_relevance: UserRelevanceOut | None = Field(alias="userRelevance", default=None)
    acknowledgement: dict[str, int | None] = Field(alias="acknowledgement", default_factory=dict)

    model_config = _alias


class ChangeDetailOut(BaseModel):
    instrument: InstrumentOut
    snapshot: MarketSnapshotOut | None = None
    previous_seen_price: float | None = Field(alias="previousSeenPrice")
    latest_signal: ChangeSignalOut | None = Field(alias="latestSignal")
    other_signals: list[ChangeSignalOut] = Field(alias="otherSignals", default_factory=list)
    last_checked_note: str | None = Field(alias="lastCheckedNote", default=None)
    # Per-instrument exchange-calendar status (spec §16). Independent of the
    # feed's global status and never inferred from data recency.
    market_status: str | None = Field(alias="marketStatus", default=None)

    model_config = _alias


class MarkSeenRequest(BaseModel):
    instrument_id: str | None = Field(alias="instrumentId", default=None)
    snapshot_ids: dict[str, int | None] | None = Field(alias="snapshotIds", default=None)

    model_config = _alias


# --------------------------------------------------------------------------- #
# Watchlist / instruments
# --------------------------------------------------------------------------- #
class WatchlistItemOut(BaseModel):
    instrument: InstrumentOut
    added_at: datetime = Field(alias="addedAt")
    # Frontend contract: READY | INSUFFICIENT
    baseline_status: Literal["READY", "INSUFFICIENT"] = Field(alias="baselineStatus")

    model_config = _alias


class WatchlistOut(BaseModel):
    items: list[WatchlistItemOut]
    updated_at: datetime = Field(alias="updatedAt")

    model_config = _alias


class WatchlistSummaryOut(BaseModel):
    id: int
    name: str
    user_id: str = Field(alias="userId")

    model_config = _alias


class AddItemRequest(BaseModel):
    instrument_id: str | None = Field(alias="instrumentId", default=None)
    # A bare provider symbol (e.g. 'TCS.NS') enables zero-seed resolution when
    # the local catalog does not yet contain the instrument.
    symbol: str | None = None

    model_config = _alias


class CreateWatchlistRequest(BaseModel):
    name: str = "My watchlist"


class InstrumentSearchResultOut(BaseModel):
    instrument: InstrumentOut


class ExploreItemOut(BaseModel):
    instrument: InstrumentOut
    snapshot: MarketSnapshotOut | None = None
    signal: ChangeSignalOut | None = None

    model_config = _alias


class ExploreOut(BaseModel):
    movers: list[ExploreItemOut]
    dippers: list[ExploreItemOut]
    unusual: list[ExploreItemOut]
    # Distinct sectors present in the discovery universe ("by sector" browsing).
    sectors: list[str]

    model_config = _alias


class ErrorOut(BaseModel):
    detail: str
