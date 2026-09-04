"""Domain enums shared across the system.

These mirror the stable domain concepts exposed by the API, not the
implementation details of any provider or database.
"""

from __future__ import annotations

from enum import Enum


class DataStatus(str, Enum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class MarketStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class ProviderStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class SignificanceTier(str, Enum):
    CRITICAL = "CRITICAL"
    SIGNIFICANT = "SIGNIFICANT"
    NOTABLE = "NOTABLE"
    NORMAL = "NORMAL"


class ChangeEventType(str, Enum):
    PRICE_ANOMALY = "PRICE_ANOMALY"
    VOLUME_ANOMALY = "VOLUME_ANOMALY"
    CORPORATE_EVENT = "CORPORATE_EVENT"
    MARKET_CONTEXT = "MARKET_CONTEXT"
    DATA_QUALITY = "DATA_QUALITY"


class CorporateEventType(str, Enum):
    EARNINGS = "EARNINGS"
    DIVIDEND = "DIVIDEND"
    STOCK_SPLIT = "STOCK_SPLIT"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"
    MAJOR_ANNOUNCEMENT = "MAJOR_ANNOUNCEMENT"
    TRADING_HALT = "TRADING_HALT"
    TRADING_RESUMPTION = "TRADING_RESUMPTION"


class CorporateEventStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class BaselineStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderFailure(str, Enum):
    """Classification of provider failures for graceful handling."""

    NETWORK = "NETWORK"
    TIMEOUT = "TIMEOUT"
    INVALID_DATA = "INVALID_DATA"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"
