"""Normalized market-data value types.

These are the types providers return and the ingestion layer consumes. They are
deliberately provider-agnostic so that swapping yfinance for another source
does not touch analytics, services, or the API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from app.domain.enums import ProviderFailure
from app.domain.entities import CorporateEvent

T = TypeVar("T")


@dataclass(frozen=True)
class ProviderResult(Generic[T]):
    """A provider response that models graceful failure.

    Rather than raising for every outage, providers classify the failure so the
    ingestion and catchup logic can decide fallback behaviour (e.g. reuse the
    last validated snapshot).
    """

    ok: bool
    value: T | None = None
    failure: ProviderFailure | None = None
    message: str | None = None
    latency_ms: int | None = None

    @classmethod
    def success(cls, value: T, latency_ms: int | None = None) -> "ProviderResult[T]":
        return cls(ok=True, value=value, latency_ms=latency_ms)

    @classmethod
    def failed(
        cls,
        failure: ProviderFailure,
        message: str | None = None,
        latency_ms: int | None = None,
    ) -> "ProviderResult[T]":
        return cls(ok=False, failure=failure, message=message, latency_ms=latency_ms)


@dataclass(frozen=True)
class MarketSnapshotCandidate:
    """A raw observation candidate collected from a provider before validation."""

    observed_at: datetime
    price: float | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    currency: str


@dataclass(frozen=True)
class HistoricalData:
    """A validated historical daily observation used for baselines."""

    observed_at: datetime
    price: float
    close: float | None
    volume: float | None


__all__ = [
    "ProviderResult",
    "MarketSnapshotCandidate",
    "HistoricalData",
    "CorporateEvent",
]
