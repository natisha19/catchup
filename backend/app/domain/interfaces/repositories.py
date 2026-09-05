"""Domain interfaces (ports).

The application layer depends on these abstractions only. Infrastructure
implementations (PostgreSQL repositories, market-data providers) live outside
the domain and are injected into services at composition time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities import (
    ChangeSignal,
    CorporateEvent,
    Instrument,
    MarketSnapshot,
    UserLastSeen,
    Watchlist,
    WatchlistItem,
)


class InstrumentRepository(Protocol):
    def get(self, instrument_id: str) -> Instrument | None: ...

    def find_by_provider_symbol(self, provider_symbol: str) -> Instrument | None: ...

    def search(self, query: str, limit: int) -> list[Instrument]: ...

    def list_active(self) -> list[Instrument]: ...

    def save(self, instrument: Instrument) -> Instrument:
        """Upsert an instrument by business key; idempotent."""


class WatchlistRepository(Protocol):
    def get_items(self, user_id: str) -> Watchlist: ...

    def add_item(self, user_id: str, instrument_id: str) -> WatchlistItem | None: ...

    def remove_item(self, user_id: str, instrument_id: str) -> bool: ...

    def has_item(self, user_id: str, instrument_id: str) -> bool: ...

    def list_watchlists(self, user_id: str) -> list: ...

    def create(self, user_id: str, name: str):
        """Create (or return the matching default) watchlist row for the user."""

    def get_by_id(self, user_id: str, watchlist_id: int):
        """Return the watchlist row if it belongs to the user, else None."""

    def get_items_for_watchlist(self, watchlist_id: int) -> Watchlist: ...

    def has_item_in(self, watchlist_id: int, instrument_id: str) -> bool: ...

    def add_item_to_watchlist(
        self, watchlist_id: int, instrument_id: str
    ) -> WatchlistItem | None: ...

    def remove_item_from_watchlist(
        self, watchlist_id: int, instrument_id: str
    ) -> bool: ...


class MarketSnapshotRepository(Protocol):
    def save(self, snapshot: MarketSnapshot) -> MarketSnapshot: ...

    def get_latest(self, instrument_id: str) -> MarketSnapshot | None: ...

    def get_latest_for(self, instrument_ids: list[str]) -> dict[str, MarketSnapshot]:
        """Latest snapshot per instrument, keyed by instrument_id."""

    def get_by_id(self, snapshot_id: int) -> MarketSnapshot | None: ...

    def history(self, instrument_id: str, limit: int) -> list[MarketSnapshot]: ...

    def count_for_instrument(self, instrument_id: str) -> int: ...


class CorporateEventRepository(Protocol):
    def save(self, event: CorporateEvent) -> CorporateEvent: ...

    def recent(self, instrument_id: str, since: datetime) -> list[CorporateEvent]: ...


class ChangeSignalRepository(Protocol):
    def save(self, signal: ChangeSignal) -> ChangeSignal: ...

    def get_latest(self, instrument_id: str) -> ChangeSignal | None: ...

    def get_for_instruments(self, instrument_ids: list[str]) -> dict[str, ChangeSignal]: ...

    def history(
        self,
        instrument_ids: list[str],
        since: datetime | None = None,
        limit: int = 200,
    ) -> dict[str, list[ChangeSignal]]:
        """All signals for the given instruments, grouped and ordered ascending."""


class UserLastSeenRepository(Protocol):
    def get(self, user_id: str, instrument_id: str) -> UserLastSeen | None: ...

    def get_all(self, user_id: str) -> dict[str, UserLastSeen]: ...

    def upsert(self, seen: UserLastSeen) -> None: ...
