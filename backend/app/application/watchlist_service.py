"""Watchlist service.

Owns the user's watchlist (add/remove/list). Uses transaction boundaries and
prevents duplicates. Baseline sufficiency is derived from persisted snapshot
history, not guessed.

Supports both the implicit default watchlist (used by the frontend) and
explicit watchlist-id operations (the full REST surface).

An optional `resolver` enables the zero-seed "add a stock" flow: when the local
catalog does not yet contain an instrument, a bare symbol (e.g. 'TCS.NS') is
resolved and persisted through the provider before it is added.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.application.instrument_service import InstrumentNotFoundError
from app.domain.entities import Instrument, Watchlist
from app.domain.enums import BaselineStatus
from app.domain.interfaces.repositories import (
    InstrumentRepository,
    MarketSnapshotRepository,
    WatchlistRepository,
)

logger = logging.getLogger(__name__)


class WatchlistNotFoundError(Exception):
    pass


class DuplicateWatchlistItemError(Exception):
    pass


class WatchlistService:
    def __init__(
        self,
        watchlists: WatchlistRepository,
        instruments: InstrumentRepository,
        snapshots: MarketSnapshotRepository,
        min_baseline_returns: int,
        resolver: Callable[[str], Instrument] | None = None,
    ) -> None:
        self._watchlists = watchlists
        self._instruments = instruments
        self._snapshots = snapshots
        self._min_baseline_returns = min_baseline_returns
        self._resolver = resolver

    # --------------------------------------------------------- explicit ids ---
    def list_watchlists(self, user_id: str) -> list[dict]:
        return [
            {"id": w.id, "name": w.name, "user_id": w.user_id}
            for w in self._watchlists.list_watchlists(user_id)
        ]

    def create_watchlist(self, user_id: str, name: str) -> dict:
        wl = self._watchlists.create(user_id, name)
        return {"id": wl.id, "name": wl.name, "user_id": wl.user_id}

    def get(self, user_id: str) -> Watchlist:
        return self._refresh(self._watchlists.get_items(user_id))

    def add_item(
        self, user_id: str, instrument_id: str | None = None, symbol: str | None = None
    ) -> None:
        inst = self._resolve_instrument(instrument_id, symbol)
        iid = inst.instrument_id
        if self._watchlists.has_item(user_id, iid):
            raise DuplicateWatchlistItemError(
                f"Instrument already in watchlist: {iid}"
            )
        self._add(self._watchlists.add_item(user_id, iid), iid)

    def remove_item(self, user_id: str, instrument_id: str) -> None:
        if not self._watchlists.remove_item(user_id, instrument_id):
            raise WatchlistNotFoundError(
                f"Instrument not in watchlist: {instrument_id}"
            )

    # -------------------------------------------------------- by id (REST) ---
    def get_for_watchlist(self, user_id: str, watchlist_id: int) -> Watchlist:
        wl = self._watchlists.get_by_id(user_id, watchlist_id)
        if wl is None:
            raise WatchlistNotFoundError(f"Watchlist not found: {watchlist_id}")
        return self._refresh(self._watchlists.get_items_for_watchlist(watchlist_id))

    def add_item_to_watchlist(
        self, user_id: str, watchlist_id: int, instrument_id: str | None = None, symbol: str | None = None
    ) -> None:
        wl = self._watchlists.get_by_id(user_id, watchlist_id)
        if wl is None:
            raise WatchlistNotFoundError(f"Watchlist not found: {watchlist_id}")
        inst = self._resolve_instrument(instrument_id, symbol)
        iid = inst.instrument_id
        if self._watchlists.has_item_in(watchlist_id, iid):
            raise DuplicateWatchlistItemError(
                f"Instrument already in watchlist: {iid}"
            )
        self._add(
            self._watchlists.add_item_to_watchlist(watchlist_id, iid), iid
        )

    def remove_item_from_watchlist(
        self, user_id: str, watchlist_id: int, instrument_id: str
    ) -> None:
        wl = self._watchlists.get_by_id(user_id, watchlist_id)
        if wl is None:
            raise WatchlistNotFoundError(f"Watchlist not found: {watchlist_id}")
        if not self._watchlists.remove_item_from_watchlist(watchlist_id, instrument_id):
            raise WatchlistNotFoundError(
                f"Instrument not in watchlist: {instrument_id}"
            )

    # ---------------------------------------------------------------- helpers
    def _resolve_instrument(
        self, instrument_id: str | None, symbol: str | None
    ) -> Instrument:
        """Return an instrument that exists locally, resolving a bare symbol if needed.

        Prefers the local catalog by instrument_id; falls back to provider
        resolution (which persists the row) when a symbol is supplied. Raises
        InstrumentNotFoundError when the instrument cannot be found or resolved.
        """
        inst = None
        if instrument_id:
            inst = self._instruments.get(instrument_id)
        if inst is None and symbol:
            if self._resolver is None:
                raise InstrumentNotFoundError(symbol)
            inst = self._resolver(symbol)
        if inst is None:
            raise InstrumentNotFoundError(instrument_id or symbol or "unknown")
        return inst

    def _add(self, added, instrument_id: str) -> None:
        if added is None:
            raise DuplicateWatchlistItemError(
                f"Instrument already in watchlist: {instrument_id}"
            )

    def _refresh(self, watchlist: Watchlist) -> Watchlist:
        from app.domain.entities import WatchlistItem

        return Watchlist(
            items=[
                WatchlistItem(
                    instrument=item.instrument,
                    added_at=item.added_at,
                    baseline_status=(
                        BaselineStatus.SUFFICIENT
                        if self._snapshots.count_for_instrument(
                            item.instrument.instrument_id
                        )
                        >= self._min_baseline_returns
                        else BaselineStatus.UNAVAILABLE
                    ),
                )
                for item in watchlist.items
            ],
            updated_at=watchlist.updated_at,
        )
