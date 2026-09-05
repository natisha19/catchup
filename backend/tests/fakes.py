"""In-memory fakes for tests.

Each fake implements one repository *Protocol* from the domain layer, so the
application services can be exercised without a database or a market provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.entities import (
    ChangeSignal,
    CorporateEvent,
    Instrument,
    MarketSnapshot,
    UserLastSeen,
    Watchlist,
    WatchlistItem,
)
from app.domain.enums import BaselineStatus, DataStatus, ProviderFailure
from app.market_data.data_types import (
    HistoricalData,
    MarketSnapshotCandidate,
    ProviderResult,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class FakeInstrumentRepo:
    _by_id: dict[str, Instrument] = field(default_factory=dict)
    _active: set[str] = field(default_factory=set)

    def add(self, inst: Instrument, active: bool = True) -> None:
        self._by_id[inst.instrument_id] = inst
        if active:
            self._active.add(inst.instrument_id)

    def save(self, instrument: Instrument) -> Instrument:
        self._by_id[instrument.instrument_id] = instrument
        self._active.add(instrument.instrument_id)
        return instrument

    def get(self, instrument_id: str) -> Instrument | None:
        return self._by_id.get(instrument_id)

    def find_by_provider_symbol(self, provider_symbol: str) -> Instrument | None:
        for inst in self._by_id.values():
            if inst.provider_symbol == provider_symbol:
                return inst
        return None

    def search(self, query: str, limit: int) -> list[Instrument]:
        q = query.lower()
        return [
            i
            for i in self._by_id.values()
            if q in i.symbol.lower() or q in i.company_name.lower()
        ][:limit]

    def list_active(self) -> list[Instrument]:
        return [self._by_id[i] for i in self._active if i in self._by_id]


@dataclass
class FakeMarketSnapshotRepo:
    _rows: dict[int, MarketSnapshot] = field(default_factory=dict)
    _counter: int = 0

    def save(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        if snapshot.id is not None:
            # update an existing row (e.g. flip to STALE)
            self._rows[snapshot.id] = snapshot
            return snapshot
        # idempotent insert by (instrument_id, observed_at, source)
        for stored in self._rows.values():
            if (
                stored.instrument_id == snapshot.instrument_id
                and stored.observed_at == snapshot.observed_at
                and stored.source == snapshot.source
            ):
                return stored
        self._counter += 1
        snapshot = MarketSnapshot(**{**snapshot.__dict__, "id": self._counter})
        self._rows[snapshot.id] = snapshot
        return snapshot

    def get_latest(self, instrument_id: str) -> MarketSnapshot | None:
        hits = [
            s for s in self._rows.values() if s.instrument_id == instrument_id
        ]
        if not hits:
            return None
        return max(hits, key=lambda s: s.observed_at)

    def get_latest_for(self, instrument_ids: list[str]) -> dict[str, MarketSnapshot]:
        out: dict[str, MarketSnapshot] = {}
        for iid in instrument_ids:
            latest = self.get_latest(iid)
            if latest is not None:
                out[iid] = latest
        return out

    def get_by_id(self, snapshot_id: int) -> MarketSnapshot | None:
        return self._rows.get(snapshot_id)

    def history(self, instrument_id: str, limit: int) -> list[MarketSnapshot]:
        hits = [s for s in self._rows.values() if s.instrument_id == instrument_id]
        hits.sort(key=lambda s: s.observed_at)
        return hits[-limit:]

    def count_for_instrument(self, instrument_id: str) -> int:
        return sum(1 for s in self._rows.values() if s.instrument_id == instrument_id)

    def _all(self) -> list[MarketSnapshot]:
        return list(self._rows.values())


@dataclass
class FakeChangeSignalRepo:
    _rows: list[ChangeSignal] = field(default_factory=list)
    _counter: int = 0

    def save(self, signal: ChangeSignal) -> ChangeSignal:
        if signal.id is None:
            # idempotent by (instrument_id, observed_at)
            for idx, existing in enumerate(self._rows):
                if (
                    existing.instrument_id == signal.instrument_id
                    and existing.observed_at == signal.observed_at
                ):
                    self._counter += 1
                    signal = ChangeSignal(**{**signal.__dict__, "id": self._counter})
                    self._rows[idx] = signal
                    return signal
            self._counter += 1
            signal = ChangeSignal(**{**signal.__dict__, "id": self._counter})
        else:
            self._rows = [
                s for s in self._rows if not (
                    s.instrument_id == signal.instrument_id
                    and s.observed_at == signal.observed_at
                )
            ]
        self._rows.append(signal)
        return signal

    def get_latest(self, instrument_id: str) -> ChangeSignal | None:
        hits = [s for s in self._rows if s.instrument_id == instrument_id]
        if not hits:
            return None
        return max(hits, key=lambda s: s.observed_at)

    def get_for_instruments(self, instrument_ids: list[str]) -> dict[str, ChangeSignal]:
        out: dict[str, ChangeSignal] = {}
        for iid in instrument_ids:
            latest = self.get_latest(iid)
            if latest is not None:
                out[iid] = latest
        return out

    def history(
        self,
        instrument_ids: list[str],
        since=None,
        limit: int = 200,
    ) -> dict[str, list[ChangeSignal]]:
        out: dict[str, list[ChangeSignal]] = {}
        for sig in self._rows:
            if sig.instrument_id not in instrument_ids:
                continue
            if since is not None and sig.observed_at < since:
                continue
            out.setdefault(sig.instrument_id, []).append(sig)
        for iid in out:
            out[iid].sort(key=lambda s: s.observed_at)
            out[iid] = out[iid][-limit:]
        return out


@dataclass
class FakeCorporateEventRepo:
    _rows: list[CorporateEvent] = field(default_factory=list)

    def save(self, event: CorporateEvent) -> CorporateEvent:
        self._rows.append(event)
        return event

    def recent(self, instrument_id: str, since: datetime) -> list[CorporateEvent]:
        return [
            e
            for e in self._rows
            if e.instrument_id == instrument_id and e.event_time >= since
        ]


@dataclass
class FakeUserLastSeenRepo:
    _rows: dict[tuple[str, str], UserLastSeen] = field(default_factory=dict)

    def get(self, user_id: str, instrument_id: str) -> UserLastSeen | None:
        return self._rows.get((user_id, instrument_id))

    def get_all(self, user_id: str) -> dict[str, UserLastSeen]:
        return {
            iid: seen
            for (uid, iid), seen in self._rows.items()
            if uid == user_id
        }

    def upsert(self, seen: UserLastSeen) -> None:
        self._rows[(seen.user_id, seen.instrument_id)] = seen


@dataclass
class FakeWatchlistRepo:
    instruments: FakeInstrumentRepo
    _items: dict[str, list[str]] = field(default_factory=dict)  # user -> [instrument_id]

    def get_items(self, user_id: str) -> Watchlist:
        ids = self._items.get(user_id, [])
        items = [
            WatchlistItem(
                instrument=self.instruments.get(iid),
                added_at=utcnow(),
                baseline_status=BaselineStatus.SUFFICIENT,
            )
            for iid in ids
            if self.instruments.get(iid) is not None
        ]
        return Watchlist(items=items, updated_at=utcnow())

    def add_item(self, user_id: str, instrument_id: str) -> WatchlistItem | None:
        inst = self.instruments.get(instrument_id)
        if inst is None:
            return None
        ids = self._items.setdefault(user_id, [])
        if instrument_id in ids:
            return None
        ids.append(instrument_id)
        return WatchlistItem(
            instrument=inst, added_at=utcnow(), baseline_status=BaselineStatus.SUFFICIENT
        )

    def remove_item(self, user_id: str, instrument_id: str) -> bool:
        ids = self._items.get(user_id, [])
        if instrument_id in ids:
            ids.remove(instrument_id)
            return True
        return False

    def has_item(self, user_id: str, instrument_id: str) -> bool:
        return instrument_id in self._items.get(user_id, [])

    def list_watchlists(self, user_id: str) -> list:
        return [{"id": 1, "name": "My watchlist", "user_id": user_id}]

    def create(self, user_id: str, name: str):
        return _Row(id=1, name=name, user_id=user_id)

    def get_by_id(self, user_id: str, watchlist_id: int):
        if watchlist_id == 1:
            return _Row(id=1, name="My watchlist", user_id=user_id)
        return None

    def get_items_for_watchlist(self, watchlist_id: int) -> Watchlist:
        if watchlist_id != 1:
            return Watchlist(items=[], updated_at=utcnow())
        return self.get_items("default-user")

    def has_item_in(self, watchlist_id: int, instrument_id: str) -> bool:
        return self.has_item("default-user", instrument_id)

    def add_item_to_watchlist(
        self, watchlist_id: int, instrument_id: str
    ) -> WatchlistItem | None:
        return self.add_item("default-user", instrument_id)

    def remove_item_from_watchlist(self, watchlist_id: int, instrument_id: str) -> bool:
        return self.remove_item("default-user", instrument_id)


@dataclass(frozen=True)
class _Row:
    id: int
    name: str
    user_id: str


def build_instrument(
    instrument_id: str = "TCS",
    symbol: str = "TCS.NS",
    company_name: str = "Tata Consultancy Services",
    exchange: str = "NSE",
    currency: str = "INR",
    provider_symbol: str | None = "TCS.NS",
    sector: str | None = "IT",
) -> Instrument:
    return Instrument(
        instrument_id=instrument_id,
        symbol=symbol,
        company_name=company_name,
        exchange=exchange,
        currency=currency,
        provider_symbol=provider_symbol,
        sector=sector,
    )


def build_snapshot(
    instrument_id: str,
    observed_at: datetime,
    price: float,
    volume: float | None = None,
    id: int | None = None,
) -> MarketSnapshot:
    return MarketSnapshot(
        instrument_id=instrument_id,
        observed_at=observed_at,
        received_at=observed_at,
        price=price,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=volume,
        currency="INR",
        source="fake",
        data_status=DataStatus.LIVE,
        id=id,
    )


@dataclass
class FakeProvider:
    """Configurable fake market provider with sensible defaults."""

    snapshots: dict[str, MarketSnapshotCandidate] = field(default_factory=dict)
    history: list[HistoricalData] = field(default_factory=list)
    events: list[CorporateEvent] = field(default_factory=list)
    resolvable: dict[str, Instrument] = field(default_factory=dict)
    snapshot_failure: ProviderFailure | None = None
    history_failure: ProviderFailure | None = None
    resolve_failure: ProviderFailure | None = None

    def source_name(self) -> str:
        return "fake"

    def resolve_instrument(self, symbol: str) -> ProviderResult[Instrument]:
        if self.resolve_failure is not None:
            return ProviderResult.failed(self.resolve_failure, "resolve down")
        inst = self.resolvable.get(symbol)
        if inst is None:
            return ProviderResult.failed(ProviderFailure.EMPTY, "unresolvable")
        return ProviderResult.success(inst)

    def get_snapshot(self, instrument: Instrument) -> ProviderResult[MarketSnapshotCandidate]:
        if self.snapshot_failure is not None:
            return ProviderResult.failed(self.snapshot_failure, "down")
        cand = self.snapshots.get(instrument.instrument_id)
        if cand is None:
            return ProviderResult.failed(ProviderFailure.EMPTY, "no data")
        return ProviderResult.success(cand)

    def get_historical_data(
        self, instrument: Instrument, start: datetime, end: datetime
    ) -> ProviderResult[list[HistoricalData]]:
        if self.history_failure is not None:
            return ProviderResult.failed(self.history_failure, "down")
        return ProviderResult.success(list(self.history))

    def get_corporate_events(
        self, instrument: Instrument, start: datetime, end: datetime
    ) -> ProviderResult[list[CorporateEvent]]:
        return ProviderResult.success(list(self.events))
