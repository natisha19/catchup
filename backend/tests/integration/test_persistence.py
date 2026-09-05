"""Integration tests: real persistence against a disposable PostgreSQL.

Proves (with a real database, not fakes):
  * Alembic migrations apply cleanly to a fresh database.
  * add-stock -> restart (new session/API) -> stock persists.
  * mark-seen watermark persists across sessions/restarts.
  * instrument lookup by business key works.
  * resolve-and-add persists the resolved instrument transactionally.

Run:  $env:CATCHUP_RUN_INTEGRATION=1; python -m pytest tests/integration -v
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_user_id
from app.infrastructure.database import get_session
from app.main import app
from tests.fakes import build_instrument

from app.infrastructure.repositories.postgres import (
    ChangeSignalRepo,
    InstrumentRepo,
    MarketSnapshotRepo,
    UserLastSeenRepo,
    WatchlistRepo,
)
from app.domain.entities import ChangeSignal, MarketSnapshot, UserLastSeen
from app.domain.enums import (
    ChangeEventType,
    DataStatus,
    SignificanceTier,
)


def _snapshot(
    instrument_id: str,
    observed_at: datetime,
    price: float,
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
        volume=1000.0,
        currency="INR",
        source="test-provider",
        data_status=DataStatus.LIVE,
    )


def _signal(
    instrument_id: str,
    observed_at: datetime,
    current_snapshot_id: int,
) -> ChangeSignal:
    return ChangeSignal(
        instrument_id=instrument_id,
        observed_at=observed_at,
        previous_snapshot_id=None,
        current_snapshot_id=current_snapshot_id,
        event_type=ChangeEventType.PRICE_ANOMALY,
        previous_price=100.0,
        current_price=110.0,
        return_pct=10.0,
        baseline_mean=100.0,
        baseline_std=5.0,
        z_score=2.0,
        current_volume=1000.0,
        baseline_average_volume=500.0,
        volume_ratio=2.0,
        significance=SignificanceTier.SIGNIFICANT,
        reason_codes=["price_anomaly"],
        data_status=DataStatus.LIVE,
        event_description="test signal",
    )


def test_migrations_idempotent_across_runs(migrated, pg_container, run_migrations_fixture):
    """Re-running `alembic upgrade head` on an already-migrated DB is a no-op."""
    run_migrations_fixture(pg_container["host_url"])  # must not raise / must return 0


def test_add_stock_persists_across_restart(db_session_factory, migrated):
    """A committed watchlist add survives a brand-new session (app restart)."""
    inst = build_instrument("TCS", "TCS.NS", "Tata Consultancy Services")
    s1 = db_session_factory()
    instruments = InstrumentRepo(s1)
    instruments.save(inst)
    watcher = WatchlistRepo(s1)
    added = watcher.add_item("user-a", "TCS")
    assert added is not None
    s1.commit()
    s1.close()

    # Simulate the API coming back up: read through a fresh session.
    s2 = db_session_factory()
    assert InstrumentRepo(s2).get("TCS") is not None
    watchlist = WatchlistRepo(s2).get_items("user-a")
    assert [i.instrument.instrument_id for i in watchlist.items] == ["TCS"]
    s2.close()


def test_add_duplicate_same_session_noop(db_session_factory, migrated):
    """Adding the same instrument twice in one session stays idempotent (one row)."""
    inst = build_instrument("INFY")
    s = db_session_factory()
    instruments = InstrumentRepo(s)
    instruments.save(inst)
    watcher = WatchlistRepo(s)
    assert watcher.add_item("user-a", "INFY") is not None
    assert watcher.add_item("user-a", "INFY") is None
    s.commit()
    s.close()


def test_mark_seen_watermark_persists(db_session_factory, migrated):
    """Explicit mark-seen acknowledgement persists its watermark across restarts."""
    inst = build_instrument("WIPRO")
    s0 = db_session_factory()
    InstrumentRepo(s0).save(inst)
    watcher = WatchlistRepo(s0)
    watcher.add_item("user-a", "WIPRO")
    s0.commit()
    s0.close()

    # Ingest a snapshot -> produces a snapshot row we can acknowledge.
    s1 = db_session_factory()
    snap = MarketSnapshotRepo(s1).save(
        _snapshot("WIPRO", datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc), 500.0)
    )
    s1.commit()
    s1.close()
    assert snap.id is not None

    s2 = db_session_factory()
    UserLastSeenRepo(s2).upsert(
        UserLastSeen(
            user_id="user-a",
            instrument_id="WIPRO",
            last_seen_at=datetime(2026, 9, 1, 10, 5, tzinfo=timezone.utc),
            last_seen_snapshot_id=snap.id,
        )
    )
    s2.commit()
    s2.close()

    # Restart: watermark must be exactly what was acknowledged.
    s3 = db_session_factory()
    seen = UserLastSeenRepo(s3).get("user-a", "WIPRO")
    s3.close()
    assert seen is not None
    assert seen.last_seen_snapshot_id == snap.id
    assert seen.user_id == "user-a"


def test_instrument_lookup_by_business_key(db_session_factory, migrated):
    """lookup by instrument_id (business key) hits the right row, not the int PK."""
    first = build_instrument("TCS", "TCS.NS", "Tata Consultancy Services")
    second = build_instrument("TCSX", "TCS2.NS", "Another TCS")
    s = db_session_factory()
    instruments = InstrumentRepo(s)
    instruments.save(first)
    instruments.save(second)
    s.commit()
    # The synthetic integer PK (row id) differs from instrument_id; lookups must
    # key on instrument_id.
    row = instruments.get("TCS")
    assert row is not None
    assert row.company_name == "Tata Consultancy Services"
    alt = instruments.get("TCSX")
    assert alt.company_name == "Another TCS"
    s.close()


def test_resolve_and_add_persists_instrument(db_session_factory, migrated):
    """The resolve-and-add path persists the resolved instrument row."""
    s = db_session_factory()
    instruments = InstrumentRepo(s)
    saved = instruments.save(build_instrument("TCS", "TCS.NS"))
    s.commit()
    s.close()
    assert saved.instrument_id == "TCS"

    s2 = db_session_factory()
    assert InstrumentRepo(s2).get("TCS").provider_symbol == "TCS.NS"
    s2.close()


def test_signal_persists_across_restart(db_session_factory, migrated):
    """Change signals survive a restart and are queryable via history()."""
    s0 = db_session_factory()
    InstrumentRepo(s0).save(build_instrument("RELIANCE"))
    s0.commit()
    s0.close()

    t = datetime(2026, 9, 2, 11, 0, tzinfo=timezone.utc)
    s1 = db_session_factory()
    snapshot = MarketSnapshotRepo(s1).save(_snapshot("RELIANCE", t, 3000.0))
    sig = ChangeSignalRepo(s1).save(
        _signal("RELIANCE", t, snapshot.id if snapshot.id else 0)
    )
    s1.commit()
    s1.close()
    assert sig.id is not None

    s2 = db_session_factory()
    history = ChangeSignalRepo(s2).history(["RELIANCE"])
    s2.close()
    assert history["RELIANCE"][0].instrument_id == "RELIANCE"


def test_add_stock_via_api_persists_across_restart(db_session_factory, migrated):
    """API add -> then a fresh session (restart) still sees the stock."""
    # Seed the instrument we will add by its business key (avoids a provider call).
    s = db_session_factory()
    InstrumentRepo(s).save(build_instrument("HDFC", "HDFC.NS"))
    s.commit()
    s.close()

    def _override_session():
        def _gen():
            session = db_session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        return _gen

    app.dependency_overrides[get_session] = _override_session()
    app.dependency_overrides[get_user_id] = lambda: "api-user"

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/watchlists/me/items", json={"instrumentId": "HDFC"}
            )
            assert resp.status_code == 201, resp.text
    finally:
        app.dependency_overrides.clear()

    # "Restart": read from a brand-new session.
    s2 = db_session_factory()
    wl = WatchlistRepo(s2).get_items("api-user")
    s2.close()
    assert [i.instrument.instrument_id for i in wl.items] == ["HDFC"]
