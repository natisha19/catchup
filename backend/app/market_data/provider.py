"""Market data provider port.

Every market-data source (yfinance today, another provider tomorrow) must
implement this abstraction. The rest of the system only ever sees normalized
domain objects and never imports a provider SDK.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities import Instrument, CorporateEvent
from app.market_data.data_types import (
    HistoricalData,
    MarketSnapshotCandidate,
    ProviderResult,
)


class MarketDataProvider(Protocol):
    """Fetches market data for an instrument.

    Return values must be normalized domain-agnostic types. Implementations are
    responsible for translating provider-specific formats.
    """

    def source_name(self) -> str: ...

    def resolve_instrument(self, symbol: str) -> ProviderResult[Instrument]:
        """Resolve and enrich a bare symbol (e.g. 'TCS.NS') into an Instrument.

        Used to bootstrap a stock that is not yet in the local catalog — the
        zero-seed "add a stock" path. Implementations must NEVER fabricate a
        symbol; a provider that cannot resolve it returns ok=False.
        """

    def get_snapshot(self, instrument: Instrument) -> ProviderResult[MarketSnapshotCandidate]: ...

    def get_historical_data(
        self,
        instrument: Instrument,
        start: datetime,
        end: datetime,
    ) -> ProviderResult[list[HistoricalData]]: ...

    def get_corporate_events(
        self,
        instrument: Instrument,
        start: datetime,
        end: datetime,
    ) -> ProviderResult[list[CorporateEvent]]: ...
