"""Instrument search/lookup/resolve service."""

from __future__ import annotations

from app.domain.entities import Instrument
from app.domain.interfaces.repositories import InstrumentRepository
from app.market_data.provider import MarketDataProvider


class InstrumentNotFoundError(Exception):
    pass


class InstrumentService:
    def __init__(
        self,
        instruments: InstrumentRepository,
        provider: MarketDataProvider | None = None,
    ) -> None:
        self._instruments = instruments
        self._provider = provider

    def search(self, query: str, limit: int = 20) -> list[Instrument]:
        return self._instruments.search(query, limit=limit)

    def get(self, instrument_id: str) -> Instrument:
        instrument = self._instruments.get(instrument_id)
        if instrument is None:
            raise InstrumentNotFoundError(instrument_id)
        return instrument

    def resolve_and_save(self, symbol: str) -> Instrument:
        """Resolve a bare symbol through the provider and persist it locally.

        Returns the persisted instrument. Raises InstrumentNotFoundError when
        no provider is available or the symbol cannot be resolved (never
        fabricates a row).
        """
        if self._provider is None:
            raise InstrumentNotFoundError(f"No provider to resolve symbol: {symbol}")
        result = self._provider.resolve_instrument(symbol)
        if not result.ok or result.value is None:
            raise InstrumentNotFoundError(f"Could not resolve symbol: {symbol}")
        return self._instruments.save(result.value)
