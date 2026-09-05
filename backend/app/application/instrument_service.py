"""Instrument search/lookup/resolve service."""

from __future__ import annotations

import logging

from app.domain.entities import Instrument
from app.domain.interfaces.repositories import InstrumentRepository
from app.market_data.catalog import InstrumentCatalog, search_score
from app.market_data.provider import MarketDataProvider

logger = logging.getLogger(__name__)


class InstrumentNotFoundError(Exception):
    pass


class InstrumentService:
    """Instrument operations.

    ``resolve_and_save`` is CATALOG-FIRST: a curated universe (the only
    authoritative answer to "what does this symbol mean?") is consulted before
    any provider. The provider may only resolve a symbol the catalog does NOT
    know, and only when that symbol is a fully-qualified provider ticker
    (contains a '.' suffix) the user explicitly supplied — a bare, ambiguous
    symbol is rejected rather than guessing.
    """

    def __init__(
        self,
        instruments: InstrumentRepository,
        provider: MarketDataProvider | None = None,
        catalog: InstrumentCatalog | None = None,
    ) -> None:
        self._instruments = instruments
        self._provider = provider
        self._catalog = catalog

    def search(self, query: str, limit: int = 20) -> list[Instrument]:
        """Catalog + local-catalog results merged, de-duplicated by business key.

        Ranked consistently with the catalog so an exact symbol always surfaces
        first regardless of which source holds the row.
        """
        merged: dict[str, Instrument] = {}
        if self._catalog is not None:
            for inst in self._catalog.search(query, limit=limit):
                merged[inst.instrument_id.upper()] = inst
        for inst in self._instruments.search(query, limit=limit):
            merged[inst.instrument_id.upper()] = inst
        ranked = sorted(merged.values(), key=lambda i: search_score(i, query))
        return ranked[:limit]

    def get(self, instrument_id: str) -> Instrument:
        instrument = self._instruments.get(instrument_id)
        if instrument is None:
            raise InstrumentNotFoundError(instrument_id)
        return instrument

    def resolve_and_save(self, symbol: str) -> Instrument:
        """Resolve ``symbol`` authoritatively, persisting the instrument.

        Raises InstrumentNotFoundError when the symbol cannot be trusted:
          * never fabricates a row;
          * never asks a provider to interpret a bare/ambiguous symbol;
          * provider fallback only for fully-qualified provider tickers
            (e.g. ``ABCD.US``) the catalog does not already know.
        """
        symbol = (symbol or "").strip().upper()
        if not symbol:
            raise InstrumentNotFoundError("No symbol supplied")

        # 1. Catalog is authoritative. SBI -> State Bank of India (SBIN), not
        #    Western Asset's "SBI" ticker.
        if self._catalog is not None:
            cataloged = self._catalog.resolve_exact(symbol)
            if cataloged is not None:
                return self._instruments.save(cataloged)

        # 2. Provider fallback: only for a fully-qualified provider ticker the
        #    catalog does not know (user explicitly gave an exchange suffix).
        if self._provider is None:
            raise InstrumentNotFoundError(f"Symbol not in supported universe: {symbol}")
        if "." not in symbol:
            raise InstrumentNotFoundError(
                f"'{symbol}' is not in the supported universe; "
                "use the NSE symbol (e.g. SBIN, TCS, RELIANCE)"
            )
        result = self._provider.resolve_instrument(symbol)
        if not result.ok or result.value is None:
            raise InstrumentNotFoundError(f"Could not resolve symbol: {symbol}")
        return self._instruments.save(result.value)