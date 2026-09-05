"""PostgreSQL repository implementations.

These adapt the SQLAlchemy ORM to the domain repository interfaces. They are the
only place that talks to the database for domain operations, so replacing
PostgreSQL later touches only this package.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities import (
    ChangeSignal,
    CorporateEvent,
    Instrument,
    MarketSnapshot,
    Watchlist,
    WatchlistItem,
    UserLastSeen,
)
from app.domain.enums import (
    BaselineStatus,
    ChangeEventType,
    CorporateEventStatus,
    CorporateEventType,
    DataStatus,
    SignificanceTier,
)
from app.infrastructure.repositories.models import (
    ChangeSignalModel,
    CorporateEventModel,
    InstrumentModel,
    MarketSnapshotModel,
    UserLastSeenModel,
    WatchlistItemModel,
    WatchlistModel,
)


def _to_dt(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _idempotent_insert(session: Session, row, select_existing, to_value):
    """Insert `row`, tolerating a concurrent duplicate.

    The INSERT is flushed inside a savepoint so a unique-constraint race rolls
    back only that insert (leaving the outer transaction usable), then re-selects
    and returns the existing row. This is the DB-level backstop that keeps
    snapshot/signal/event ingestion idempotent even under concurrency. Returns
    None when the fresh insert committed to the savepoint (caller flushes again
    and builds the new value).
    """
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError:
        existing = session.execute(select_existing).scalar_one_or_none()
        if existing is not None:
            return to_value(existing)
        raise
    return None


class InstrumentRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, instrument_id: str) -> Instrument | None:
        row = self._session.execute(
            select(InstrumentModel).where(InstrumentModel.instrument_id == instrument_id)
        ).scalar_one_or_none()
        return _to_instrument(row) if row else None

    def find_by_provider_symbol(self, provider_symbol: str) -> Instrument | None:
        row = self._session.execute(
            select(InstrumentModel).where(InstrumentModel.provider_symbol == provider_symbol)
        ).scalar_one_or_none()
        return _to_instrument(row) if row else None

    def search(self, query: str, limit: int = 20) -> list[Instrument]:
        q = query.strip()
        if not q:
            return []
        like = f"%{q.upper()}%"
        rows = self._session.execute(
            select(InstrumentModel)
            .where(
                or_(
                    InstrumentModel.symbol.ilike(like),
                    InstrumentModel.company_name.ilike(like),
                )
            )
            .limit(limit)
        ).scalars().all()
        return [_to_instrument(r) for r in rows if r]

    def list_active(self) -> list[Instrument]:
        # Only poll symbols that at least one user actively watches.  A removed
        # symbol stays in the catalog/search index, but it no longer consumes
        # provider capacity on every ingestion cycle.
        rows = self._session.execute(
            select(InstrumentModel)
            .join(
                WatchlistItemModel,
                WatchlistItemModel.instrument_id == InstrumentModel.instrument_id,
            )
            .where(WatchlistItemModel.removed_at.is_(None))
            .distinct()
        ).scalars().all()
        return [_to_instrument(r) for r in rows if r]

    def save(self, instrument: Instrument) -> Instrument:
        """Upsert an instrument by its business key (instrument_id).

        Idempotent: re-saving an existing instrument updates its provider-facing
        fields and returns the same row rather than creating a duplicate.
        """
        row = self._session.execute(
            select(InstrumentModel).where(InstrumentModel.instrument_id == instrument.instrument_id)
        ).scalar_one_or_none()
        if row is None:
            row = InstrumentModel(instrument_id=instrument.instrument_id)
            self._session.add(row)
        row.symbol = instrument.symbol
        row.company_name = instrument.company_name
        row.exchange = instrument.exchange
        row.currency = instrument.currency
        row.provider_symbol = instrument.provider_symbol
        row.sector = instrument.sector
        self._session.flush()
        return _to_instrument(row)


class WatchlistRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _default_watchlist(self, user_id: str) -> WatchlistModel:
        return self._get_or_create(user_id, "My watchlist")

    def _get_or_create(self, user_id: str, name: str) -> WatchlistModel:
        wl = self._session.execute(
            select(WatchlistModel).where(WatchlistModel.user_id == user_id)
        ).scalars().first()
        if wl is None:
            wl = WatchlistModel(user_id=user_id, name=name)
            self._session.add(wl)
            self._session.flush()
        return wl

    def list_watchlists(self, user_id: str) -> list[WatchlistModel]:
        rows = self._session.execute(
            select(WatchlistModel).where(WatchlistModel.user_id == user_id).order_by(WatchlistModel.id)
        ).scalars().all()
        return list(rows)

    def create(self, user_id: str, name: str) -> WatchlistModel:
        if name == "My watchlist":
            existing = self._session.execute(
                select(WatchlistModel).where(WatchlistModel.user_id == user_id, WatchlistModel.name == name)
            ).scalars().first()
            if existing:
                return existing
        wl = WatchlistModel(user_id=user_id, name=name)
        self._session.add(wl)
        self._session.flush()
        return wl

    def get_by_id(self, user_id: str, watchlist_id: int) -> WatchlistModel | None:
        return self._session.execute(
            select(WatchlistModel).where(
                WatchlistModel.id == watchlist_id,
                WatchlistModel.user_id == user_id,
            )
        ).scalar_one_or_none()

    def get_items(self, user_id: str) -> Watchlist:
        wl = self._default_watchlist(user_id)
        return self._watchlist_rows(wl.id)

    def get_items_for_watchlist(self, watchlist_id: int) -> Watchlist:
        return self._watchlist_rows(watchlist_id)

    def _watchlist_rows(self, watchlist_id: int) -> Watchlist:
        rows = self._session.execute(
            select(WatchlistItemModel, InstrumentModel)
            .join(InstrumentModel, InstrumentModel.instrument_id == WatchlistItemModel.instrument_id)
            .where(
                WatchlistItemModel.watchlist_id == watchlist_id,
                WatchlistItemModel.removed_at.is_(None),
            )
            .order_by(WatchlistItemModel.created_at)
        ).all()
        items = [
            WatchlistItem(
                instrument=_to_instrument(inst),
                added_at=_to_dt(item.created_at) or datetime.now(timezone.utc),
                baseline_status=_baseline_status(inst),
            )
            for item, inst in rows
        ]
        return Watchlist(items=items, updated_at=datetime.now(timezone.utc))

    def has_item(self, user_id: str, instrument_id: str) -> bool:
        wl = self._default_watchlist(user_id)
        return self._has_item_in(wl.id, instrument_id)

    def has_item_in(self, watchlist_id: int, instrument_id: str) -> bool:
        return self._has_item_in(watchlist_id, instrument_id)

    def _has_item_in(self, watchlist_id: int, instrument_id: str) -> bool:
        return self._session.execute(
            select(WatchlistItemModel).where(
                WatchlistItemModel.watchlist_id == watchlist_id,
                WatchlistItemModel.instrument_id == instrument_id,
                WatchlistItemModel.removed_at.is_(None),
            )
        ).scalar_one_or_none() is not None

    def add_item(self, user_id: str, instrument_id: str) -> WatchlistItem | None:
        wl = self._default_watchlist(user_id)
        return self._add_item_in(wl.id, instrument_id)

    def add_item_to_watchlist(
        self, watchlist_id: int, instrument_id: str
    ) -> WatchlistItem | None:
        return self._add_item_in(watchlist_id, instrument_id)

    def _add_item_in(self, watchlist_id: int, instrument_id: str) -> WatchlistItem | None:
        if self._has_item_in(watchlist_id, instrument_id):
            return None  # already present; idempotent add
        inst = self._session.execute(
            select(InstrumentModel).where(InstrumentModel.instrument_id == instrument_id)
        ).scalar_one_or_none()
        if inst is None:
            return None
        item = WatchlistItemModel(watchlist_id=watchlist_id, instrument_id=instrument_id)
        self._session.add(item)
        self._session.flush()
        return WatchlistItem(
            instrument=_to_instrument(inst),
            added_at=_to_dt(item.created_at) or datetime.now(timezone.utc),
            baseline_status=_baseline_status(inst),
        )

    def remove_item(self, user_id: str, instrument_id: str) -> bool:
        wl = self._default_watchlist(user_id)
        return self._remove_item_in(wl.id, instrument_id)

    def remove_item_from_watchlist(self, watchlist_id: int, instrument_id: str) -> bool:
        return self._remove_item_in(watchlist_id, instrument_id)

    def _remove_item_in(self, watchlist_id: int, instrument_id: str) -> bool:
        item = self._session.execute(
            select(WatchlistItemModel).where(
                WatchlistItemModel.watchlist_id == watchlist_id,
                WatchlistItemModel.instrument_id == instrument_id,
                WatchlistItemModel.removed_at.is_(None),
            )
        ).scalar_one_or_none()
        if item is None:
            return False
        item.removed_at = datetime.now(timezone.utc)
        self._session.flush()
        return True


class MarketSnapshotRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        # An explicit id means "update this persisted row" (e.g. flipping an
        # existing snapshot to STALE after a provider failure).
        if snapshot.id is not None:
            row = self._session.get(MarketSnapshotModel, snapshot.id)
            if row is not None:
                row.price = snapshot.price
                row.open = snapshot.open
                row.high = snapshot.high
                row.low = snapshot.low
                row.close = snapshot.close
                row.volume = snapshot.volume
                row.data_status = snapshot.data_status.value
                self._session.flush()
                return _to_snapshot(row)

        # Otherwise idempotently insert by (instrument_id, observed_at, source):
        # re-ingesting the same observation must not create a duplicate. The
        # unique constraint is the backstop; the look-up avoids raising on a
        # no-op re-ingest.
        existing = self._session.execute(
            select(MarketSnapshotModel).where(
                MarketSnapshotModel.instrument_id == snapshot.instrument_id,
                MarketSnapshotModel.observed_at == snapshot.observed_at,
                MarketSnapshotModel.source == snapshot.source,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return _to_snapshot(existing)

        row = MarketSnapshotModel(
            instrument_id=snapshot.instrument_id,
            observed_at=snapshot.observed_at,
            received_at=snapshot.received_at,
            price=snapshot.price,
            open=snapshot.open,
            high=snapshot.high,
            low=snapshot.low,
            close=snapshot.close,
            volume=snapshot.volume,
            currency=snapshot.currency,
            source=snapshot.source,
            data_status=snapshot.data_status.value,
        )
        existing = _idempotent_insert(
            self._session,
            row,
            select(MarketSnapshotModel).where(
                MarketSnapshotModel.instrument_id == snapshot.instrument_id,
                MarketSnapshotModel.observed_at == snapshot.observed_at,
                MarketSnapshotModel.source == snapshot.source,
            ),
            _to_snapshot,
        )
        if existing is not None:
            return existing
        self._session.flush()
        return MarketSnapshot(
            id=row.id,
            instrument_id=row.instrument_id,
            observed_at=_to_dt(row.observed_at) or row.observed_at,
            received_at=_to_dt(row.received_at),
            price=row.price,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            currency=row.currency,
            source=row.source,
            data_status=DataStatus(row.data_status),
        )

    def get_by_id(self, snapshot_id: int) -> MarketSnapshot | None:
        row = self._session.get(MarketSnapshotModel, snapshot_id)
        return _to_snapshot(row) if row else None

    def get_latest(self, instrument_id: str) -> MarketSnapshot | None:
        row = self._session.execute(
            select(MarketSnapshotModel)
            .where(MarketSnapshotModel.instrument_id == instrument_id)
            .order_by(MarketSnapshotModel.observed_at.desc(), MarketSnapshotModel.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        return _to_snapshot(row) if row else None

    def get_latest_for(self, instrument_ids: list[str]) -> dict[str, MarketSnapshot]:
        if not instrument_ids:
            return {}
        rows = self._session.execute(
            select(MarketSnapshotModel)
            .where(MarketSnapshotModel.instrument_id.in_(instrument_ids))
            .order_by(
                MarketSnapshotModel.instrument_id,
                MarketSnapshotModel.observed_at.desc(),
                MarketSnapshotModel.id.desc(),
            )
        ).scalars().all()
        latest: dict[str, MarketSnapshot] = {}
        for r in rows:
            if r.instrument_id not in latest:
                latest[r.instrument_id] = _to_snapshot(r)
        return latest

    def history(self, instrument_id: str, limit: int) -> list[MarketSnapshot]:
        rows = self._session.execute(
            select(MarketSnapshotModel)
            .where(MarketSnapshotModel.instrument_id == instrument_id)
            .order_by(MarketSnapshotModel.observed_at.desc())
            .limit(limit)
        ).scalars().all()
        return [_to_snapshot(r) for r in rows if r]

    def count_for_instrument(self, instrument_id: str) -> int:
        return int(self._session.execute(
            select(func.count(MarketSnapshotModel.id)).where(
                MarketSnapshotModel.instrument_id == instrument_id
            )
        ).scalar_one())


class CorporateEventRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, event: CorporateEvent) -> CorporateEvent:
        row = CorporateEventModel(
            instrument_id=event.instrument_id,
            event_type=event.event_type.value,
            event_time=event.event_time,
            description=event.description,
            source=event.source,
            status=event.status.value,
            raw_reference=event.raw_reference,
        )
        existing = _idempotent_insert(
            self._session,
            row,
            select(CorporateEventModel).where(
                CorporateEventModel.instrument_id == event.instrument_id,
                CorporateEventModel.event_type == event.event_type.value,
                CorporateEventModel.event_time == event.event_time,
            ),
            _to_corporate_event,
        )
        if existing is not None:
            return existing
        self._session.flush()
        return CorporateEvent(
            id=row.id,
            instrument_id=row.instrument_id,
            event_type=event.event_type,
            event_time=_to_dt(row.event_time) or row.event_time,
            description=row.description,
            source=row.source,
            status=event.status,
            raw_reference=row.raw_reference,
        )

    def recent(self, instrument_id: str, since: object) -> list[CorporateEvent]:
        rows = self._session.execute(
            select(CorporateEventModel)
            .where(
                CorporateEventModel.instrument_id == instrument_id,
                CorporateEventModel.event_time >= since,
            )
            .order_by(CorporateEventModel.event_time.desc())
        ).scalars().all()
        events: list[CorporateEvent] = []
        for r in rows:
            events.append(
                CorporateEvent(
                    id=r.id,
                    instrument_id=r.instrument_id,
                    event_type=CorporateEventType(r.event_type),
                    event_time=_to_dt(r.event_time) or r.event_time,
                    description=r.description,
                    source=r.source,
                    status=CorporateEventStatus(r.status),
                    raw_reference=r.raw_reference,
                )
            )
        return events


class ChangeSignalRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, signal: ChangeSignal) -> ChangeSignal:
        # Idempotent by (instrument_id, observed_at): one snapshot yields one
        # signal. Re-ingesting the same observation updates, never duplicates.
        existing = self._session.execute(
            select(ChangeSignalModel).where(
                ChangeSignalModel.instrument_id == signal.instrument_id,
                ChangeSignalModel.observed_at == signal.observed_at,
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.event_type = signal.event_type.value
            existing.previous_snapshot_id = signal.previous_snapshot_id
            existing.current_snapshot_id = signal.current_snapshot_id
            existing.previous_price = signal.previous_price
            existing.current_price = signal.current_price
            existing.return_pct = signal.return_pct
            existing.baseline_mean = signal.baseline_mean
            existing.baseline_std = signal.baseline_std
            existing.z_score = signal.z_score
            existing.current_volume = signal.current_volume
            existing.baseline_average_volume = signal.baseline_average_volume
            existing.volume_ratio = signal.volume_ratio
            existing.significance = signal.significance.value
            existing.reason_codes = json.dumps(signal.reason_codes)
            existing.data_status = signal.data_status.value
            existing.event_description = signal.event_description
            self._session.flush()
            return _to_signal(existing)

        row = ChangeSignalModel(
            instrument_id=signal.instrument_id,
            observed_at=signal.observed_at,
            previous_snapshot_id=signal.previous_snapshot_id,
            current_snapshot_id=signal.current_snapshot_id,
            event_type=signal.event_type.value,
            previous_price=signal.previous_price,
            current_price=signal.current_price,
            return_pct=signal.return_pct,
            baseline_mean=signal.baseline_mean,
            baseline_std=signal.baseline_std,
            z_score=signal.z_score,
            current_volume=signal.current_volume,
            baseline_average_volume=signal.baseline_average_volume,
            volume_ratio=signal.volume_ratio,
            significance=signal.significance.value,
            reason_codes=json.dumps(signal.reason_codes),
            data_status=signal.data_status.value,
            event_description=signal.event_description,
        )
        existing = _idempotent_insert(
            self._session,
            row,
            select(ChangeSignalModel).where(
                ChangeSignalModel.instrument_id == signal.instrument_id,
                ChangeSignalModel.observed_at == signal.observed_at,
            ),
            _to_signal,
        )
        if existing is not None:
            return existing
        self._session.flush()
        return _to_signal(row)

    def get_latest(self, instrument_id: str) -> ChangeSignal | None:
        row = self._session.execute(
            select(ChangeSignalModel)
            .where(ChangeSignalModel.instrument_id == instrument_id)
            .order_by(ChangeSignalModel.observed_at.desc(), ChangeSignalModel.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        return _to_signal(row) if row else None

    def get_for_instruments(self, instrument_ids: list[str]) -> dict[str, ChangeSignal]:
        if not instrument_ids:
            return {}
        rows = self._session.execute(
            select(ChangeSignalModel)
            .where(ChangeSignalModel.instrument_id.in_(instrument_ids))
            .order_by(ChangeSignalModel.observed_at.asc(), ChangeSignalModel.id.asc())
        ).scalars().all()
        latest: dict[str, ChangeSignal] = {}
        for r in rows:
            sig = _to_signal(r)
            latest[sig.instrument_id] = sig
        return latest

    def history(
        self,
        instrument_ids: list[str],
        since: datetime | None = None,
        limit: int = 200,
    ) -> dict[str, list[ChangeSignal]]:
        if not instrument_ids:
            return {}
        stmt = select(ChangeSignalModel).where(
            ChangeSignalModel.instrument_id.in_(instrument_ids)
        )
        if since is not None:
            stmt = stmt.where(ChangeSignalModel.observed_at >= since)
        stmt = stmt.order_by(
            ChangeSignalModel.observed_at.asc(), ChangeSignalModel.id.asc()
        )
        rows = self._session.execute(stmt).scalars().all()
        out: dict[str, list[ChangeSignal]] = {}
        for r in rows:
            sig = _to_signal(r)
            out.setdefault(sig.instrument_id, []).append(sig)
        for iid, sigs in out.items():
            out[iid] = sigs[-limit:]
        return out


class UserLastSeenRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: str, instrument_id: str) -> UserLastSeen | None:
        row = self._session.execute(
            select(UserLastSeenModel).where(
                UserLastSeenModel.user_id == user_id,
                UserLastSeenModel.instrument_id == instrument_id,
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return UserLastSeen(
            user_id=row.user_id,
            instrument_id=row.instrument_id,
            last_seen_at=_to_dt(row.last_seen_at) or row.last_seen_at,
            last_seen_snapshot_id=row.last_seen_snapshot_id,
        )

    def get_all(self, user_id: str) -> dict[str, UserLastSeen]:
        rows = self._session.execute(
            select(UserLastSeenModel).where(UserLastSeenModel.user_id == user_id)
        ).scalars().all()
        result: dict[str, UserLastSeen] = {}
        for row in rows:
            result[row.instrument_id] = UserLastSeen(
                user_id=row.user_id,
                instrument_id=row.instrument_id,
                last_seen_at=_to_dt(row.last_seen_at) or row.last_seen_at,
                last_seen_snapshot_id=row.last_seen_snapshot_id,
            )
        return result

    def upsert(self, seen: UserLastSeen) -> None:
        row = self._session.execute(
            select(UserLastSeenModel).where(
                UserLastSeenModel.user_id == seen.user_id,
                UserLastSeenModel.instrument_id == seen.instrument_id,
            )
        ).scalar_one_or_none()
        if row is None:
            row = UserLastSeenModel(
                user_id=seen.user_id,
                instrument_id=seen.instrument_id,
            )
            self._session.add(row)
        row.last_seen_at = seen.last_seen_at
        row.last_seen_snapshot_id = seen.last_seen_snapshot_id
        self._session.flush()


# -- mappers ----------------------------------------------------------------


def _to_instrument(row: InstrumentModel) -> Instrument:
    return Instrument(
        instrument_id=row.instrument_id,
        symbol=row.symbol,
        company_name=row.company_name,
        exchange=row.exchange,
        currency=row.currency,
        provider_symbol=row.provider_symbol,
        sector=row.sector,
    )


def _to_corporate_event(row: CorporateEventModel) -> CorporateEvent:
    return CorporateEvent(
        id=row.id,
        instrument_id=row.instrument_id,
        event_type=CorporateEventType(row.event_type),
        event_time=_to_dt(row.event_time) or row.event_time,
        description=row.description,
        source=row.source,
        status=CorporateEventStatus(row.status),
        raw_reference=row.raw_reference,
    )


def _to_snapshot(row: MarketSnapshotModel) -> MarketSnapshot:
    return MarketSnapshot(
        id=row.id,
        instrument_id=row.instrument_id,
        observed_at=_to_dt(row.observed_at) or row.observed_at,
        received_at=_to_dt(row.received_at),
        price=row.price,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        currency=row.currency,
        source=row.source,
        data_status=DataStatus(row.data_status),
    )


def _to_signal(row: ChangeSignalModel) -> ChangeSignal:
    codes = []
    try:
        codes = json.loads(row.reason_codes or "[]")
    except (ValueError, TypeError):
        codes = []
    return ChangeSignal(
        id=row.id,
        instrument_id=row.instrument_id,
        observed_at=_to_dt(row.observed_at) or row.observed_at,
        previous_snapshot_id=row.previous_snapshot_id,
        current_snapshot_id=row.current_snapshot_id,
        event_type=ChangeEventType(row.event_type),
        previous_price=row.previous_price,
        current_price=row.current_price,
        return_pct=row.return_pct,
        baseline_mean=row.baseline_mean,
        baseline_std=row.baseline_std,
        z_score=row.z_score,
        current_volume=row.current_volume,
        baseline_average_volume=row.baseline_average_volume,
        volume_ratio=row.volume_ratio,
        significance=SignificanceTier(row.significance),
        reason_codes=codes,
        data_status=DataStatus(row.data_status),
        event_description=row.event_description or "",
    )


def _baseline_status(inst: InstrumentModel) -> BaselineStatus:
    # Baseline sufficiency depends on snapshot history, computed by the service.
    # Here we return a reasonable default that the service refines. We do not
    # run expensive queries in a list mapper; services override with real counts.
    return BaselineStatus.SUFFICIENT
