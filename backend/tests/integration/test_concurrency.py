"""Integration tests: concurrency and uniqueness against real PostgreSQL.

Proves the database-level invariants survive real concurrency and repeated
ingestion:
  * exactly one market snapshot per (instrument, observed_at, source);
  * exactly one change signal per (instrument, observed_at);
  * at most one ACTIVE watchlist row per (watchlist, instrument) — enforced by
    the partial unique index, since Postgres treats NULL removed_at as distinct
    under a plain unique constraint.

The "concurrent duplicate" cases are orchestrated so the winner holds the unique
key uncommitted while the loser blocks, then the winner commits to unblock the
loser — exercising the IntegrityError backstop (savepoint rollback + re-select)
deterministically, without a genuine lock deadlock.

Run:  $env:CATCHUP_RUN_INTEGRATION=1; python -m pytest tests/integration -v
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from tests.fakes import build_instrument

from app.infrastructure.repositories.postgres import (
    ChangeSignalRepo,
    InstrumentRepo,
    MarketSnapshotRepo,
    WatchlistRepo,
)
from app.infrastructure.repositories.models import WatchlistItemModel
from app.domain.entities import ChangeSignal, MarketSnapshot
from app.domain.enums import ChangeEventType, DataStatus, SignificanceTier

WINNER_SLEEP = 0.5


def _snapshot(key: str, observed_at: datetime, price: float) -> MarketSnapshot:
    return MarketSnapshot(
        instrument_id=key,
        observed_at=observed_at,
        received_at=observed_at,
        price=price,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1000.0,
        currency="INR",
        source="test-provider",
        data_status=DataStatus.LIVE,
    )


def _signal(key: str, observed_at: datetime) -> ChangeSignal:
    return ChangeSignal(
        instrument_id=key,
        observed_at=observed_at,
        previous_snapshot_id=None,
        current_snapshot_id=1,
        event_type=ChangeEventType.PRICE_ANOMALY,
        previous_price=100.0,
        current_price=108.0,
        return_pct=8.0,
        baseline_mean=100.0,
        baseline_std=4.0,
        z_score=2.0,
        current_volume=1000.0,
        baseline_average_volume=500.0,
        volume_ratio=2.0,
        significance=SignificanceTier.SIGNIFICANT,
        reason_codes=["price_anomaly"],
        data_status=DataStatus.LIVE,
        event_description="test",
    )


def _run_duplicate_race(session_factory, winner_save, loser_save):
    """Winner holds the unique key uncommitted while the loser blocks on it.

    Returns the (winner_value, loser_value) after both complete.
    """
    winner_session = session_factory()
    loser_session = session_factory()

    # Winner: INSERT + flush acquires the unique-key lock; transaction stays open.
    winner_value = winner_save(winner_session)
    assert winner_value.id is not None

    committer = threading.Thread(
        target=lambda: (time.sleep(WINNER_SLEEP), winner_session.commit())
    )
    committer.start()

    # Loser: runs its select (sees nothing, winner uncommitted), then its INSERT
    # blocks on the winner's lock; when the committer commits, it raises
    # IntegrityError which the backstop converts into a re-select of the winner.
    loser_value = loser_save(loser_session)
    committer.join()
    winner_session.close()
    loser_session.close()
    return winner_value, loser_value


@pytest.fixture()
def seed_instrument(db_session_factory, migrated):
    def _seed(key: str) -> None:
        s = db_session_factory()
        InstrumentRepo(s).save(build_instrument(key))
        s.commit()
        s.close()
    return _seed


def test_concurrent_snapshot_dedup_single_row(seed_instrument, db_session_factory):
    """Concurrent ingest of the same observation dedups to exactly one row."""
    t = datetime(2026, 9, 3, 9, 30, tzinfo=timezone.utc)
    seed_instrument("SNAPX")

    winner, loser = _run_duplicate_race(
        db_session_factory,
        lambda s: MarketSnapshotRepo(s).save(_snapshot("SNAPX", t, 123.0)),
        lambda s: MarketSnapshotRepo(s).save(_snapshot("SNAPX", t, 123.0)),
    )
    assert loser.id == winner.id, "concurrent duplicate save returned different rows"
    s3 = db_session_factory()
    assert MarketSnapshotRepo(s3).count_for_instrument("SNAPX") == 1
    s3.close()


def test_concurrent_signal_dedup_single_row(seed_instrument, db_session_factory):
    """Concurrent persistence of the same signal dedups to exactly one row."""
    t = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)
    seed_instrument("SIGX")

    winner, loser = _run_duplicate_race(
        db_session_factory,
        lambda s: ChangeSignalRepo(s).save(_signal("SIGX", t)),
        lambda s: ChangeSignalRepo(s).save(_signal("SIGX", t)),
    )
    assert loser.id == winner.id, "concurrent signal save returned different rows"
    s3 = db_session_factory()
    rows = ChangeSignalRepo(s3).history(["SIGX"])
    s3.close()
    assert len(rows["SIGX"]) == 1


def test_sequential_snapshot_resave_is_idempotent(seed_instrument, db_session_factory):
    """Re-saving the same snapshot after a restart keeps a single row."""
    t = datetime(2026, 9, 3, 10, 30, tzinfo=timezone.utc)
    seed_instrument("SNAPY")

    s1 = db_session_factory()
    first = MarketSnapshotRepo(s1).save(_snapshot("SNAPY", t, 55.0))
    s1.commit()
    s1.close()

    s2 = db_session_factory()
    second = MarketSnapshotRepo(s2).save(_snapshot("SNAPY", t, 55.0))
    s2.commit()
    s2.close()

    assert first.id == second.id
    s3 = db_session_factory()
    assert MarketSnapshotRepo(s3).count_for_instrument("SNAPY") == 1
    s3.close()


def test_sequential_signal_resave_is_idempotent(seed_instrument, db_session_factory):
    """Re-saving the same signal after a restart keeps a single row."""
    t = datetime(2026, 9, 3, 11, 0, tzinfo=timezone.utc)
    seed_instrument("SIGY")

    s1 = db_session_factory()
    first = ChangeSignalRepo(s1).save(_signal("SIGY", t))
    s1.commit()
    s1.close()

    s2 = db_session_factory()
    second = ChangeSignalRepo(s2).save(_signal("SIGY", t))
    s2.commit()
    s2.close()

    assert first.id == second.id
    s3 = db_session_factory()
    rows = ChangeSignalRepo(s3).history(["SIGY"])
    s3.close()
    assert len(rows["SIGY"]) == 1


def test_concurrent_watchlist_active_duplicate_blocked(seed_instrument, db_session_factory):
    """Partial unique index prevents two ACTIVE rows for the same watchlist+instrument."""
    seed_instrument("WLDUPE")

    s = db_session_factory()
    watchlists = WatchlistRepo(s)
    watchlists.get_items("user-a")  # creates the default watchlist
    wl_id = watchlists.list_watchlists("user-a")[0].id
    s.commit()
    s.close()

    sa = db_session_factory()
    sb = db_session_factory()
    sa.add(WatchlistItemModel(watchlist_id=wl_id, instrument_id="WLDUPE"))
    sb.add(WatchlistItemModel(watchlist_id=wl_id, instrument_id="WLDUPE"))
    sa.commit()
    with pytest.raises(IntegrityError):
        sb.commit()
    sb.rollback()
    sa.close()
    sb.close()

    s3 = db_session_factory()
    count = s3.execute(
        select(WatchlistItemModel).where(
            WatchlistItemModel.watchlist_id == wl_id,
            WatchlistItemModel.instrument_id == "WLDUPE",
        )
    ).scalars().all()
    s3.close()
    assert len(count) == 1


def test_watchlist_removed_then_readded_allows_new_active_row(seed_instrument, db_session_factory):
    """Soft-deleted row is not blocked; a fresh active add is permitted."""
    seed_instrument("WLROLL")

    s = db_session_factory()
    watchlists = WatchlistRepo(s)
    watchlists.get_items("user-a")
    wl_id = watchlists.list_watchlists("user-a")[0].id
    assert watchlists.add_item("user-a", "WLROLL") is not None
    assert watchlists.remove_item("user-a", "WLROLL") is True
    assert watchlists.add_item("user-a", "WLROLL") is not None
    s.commit()
    s.close()

    s2 = db_session_factory()
    active = [i.instrument.instrument_id for i in WatchlistRepo(s2).get_items("user-a").items]
    s2.close()
    assert active == ["WLROLL"]
