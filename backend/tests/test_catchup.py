"""Catchup service tests: per-user last-seen diff, visibility, provider status."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.application.catchup_service import CatchupService
from app.domain.entities import (
    ChangeSignal,
    MarketSnapshot,
    UserLastSeen,
)
from app.domain.enums import (
    ChangeEventType,
    DataStatus,
    MarketStatus,
    SignificanceTier,
)
from app.relevance.ranking import RuleBasedRelevanceRanker
from tests.fakes import (
    FakeChangeSignalRepo,
    FakeInstrumentRepo,
    FakeMarketSnapshotRepo,
    FakeUserLastSeenRepo,
    FakeWatchlistRepo,
    build_instrument,
)

T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2024, 1, 2, tzinfo=timezone.utc)
T2 = datetime(2024, 1, 3, tzinfo=timezone.utc)


def make_snapshot(iid, t, price, sid):
    return MarketSnapshot(
        instrument_id=iid,
        observed_at=t,
        received_at=t,
        price=price,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1000.0,
        currency="INR",
        source="fake",
        data_status=DataStatus.LIVE,
        id=sid,
    )


def make_signal(iid, t, tier: SignificanceTier, current_sid, desc="X"):
    return ChangeSignal(
        instrument_id=iid,
        observed_at=t,
        previous_snapshot_id=current_sid - 1,
        current_snapshot_id=current_sid,
        event_type=ChangeEventType.PRICE_ANOMALY,
        previous_price=100.0,
        current_price=110.0,
        return_pct=10.0,
        baseline_mean=0.0,
        baseline_std=2.0,
        z_score=5.0,
        current_volume=1000.0,
        baseline_average_volume=500.0,
        volume_ratio=2.0,
        significance=tier,
        reason_codes=["SIGNIFICANT_PRICE_MOVE"],
        data_status=DataStatus.LIVE,
        event_description=desc,
    )


def build_service(snapshots=None, signals=None, last_seen=None, watchlists=None, instruments=None):
    instruments = instruments or FakeInstrumentRepo()
    inst = build_instrument()
    instruments.add(inst)
    return CatchupService(
        watchlists=watchlists or FakeWatchlistRepo(instruments),
        instruments=instruments,
        snapshots=snapshots or FakeMarketSnapshotRepo(),
        signals=signals or FakeChangeSignalRepo(),
        last_seen=last_seen or FakeUserLastSeenRepo(),
        ranker=RuleBasedRelevanceRanker(),
        min_baseline_returns=20,
        stale_threshold_minutes=30,
    )


def service_for_user(user_id, *, snapshots=None, signals=None, last_seen=None):
    instruments = FakeInstrumentRepo()
    instruments.add(build_instrument())
    watchlists = FakeWatchlistRepo(instruments)
    watchlists.add_item(user_id, "TCS")
    return build_service(
        snapshots=snapshots,
        signals=signals,
        last_seen=last_seen,
        watchlists=watchlists,
        instruments=instruments,
    )


class TestLastSeenPerUser:
    def test_user_who_saw_latest_snapshot_sees_no_change(self):
        snapshots = FakeMarketSnapshotRepo()
        snapshots.save(make_snapshot("TCS", T1, 100.0, 1))
        snapshots.save(make_snapshot("TCS", T2, 110.0, 2))

        signals = FakeChangeSignalRepo()
        signals.save(make_signal("TCS", T2, SignificanceTier.CRITICAL, current_sid=2))

        last_seen = FakeUserLastSeenRepo()
        # Alice has already seen the latest snapshot.
        last_seen.upsert(UserLastSeen(user_id="alice", instrument_id="TCS",
                                      last_seen_at=T2, last_seen_snapshot_id=2))

        svc = service_for_user("alice", snapshots=snapshots, signals=signals, last_seen=last_seen)

        feed = svc.get_feed("alice")
        assert feed.changes == []
        assert feed.unchanged_count >= 1

    def test_user_who_has_not_seen_latest_sees_critical_change(self):
        snapshots = FakeMarketSnapshotRepo()
        snapshots.save(make_snapshot("TCS", T1, 100.0, 1))
        snapshots.save(make_snapshot("TCS", T2, 110.0, 2))

        signals = FakeChangeSignalRepo()
        signals.save(make_signal("TCS", T2, SignificanceTier.CRITICAL, current_sid=2))

        last_seen = FakeUserLastSeenRepo()
        # Bob has only seen the older snapshot.
        last_seen.upsert(UserLastSeen(user_id="bob", instrument_id="TCS",
                                      last_seen_at=T1, last_seen_snapshot_id=1))

        svc = service_for_user("bob", snapshots=snapshots, signals=signals, last_seen=last_seen)

        feed = svc.get_feed("bob")
        assert len(feed.changes) == 1
        assert feed.changes[0].instrument_id == "TCS"
        assert feed.changes[0].significance is SignificanceTier.CRITICAL

    def test_first_time_user_sees_all_significant_changes(self):
        snapshots = FakeMarketSnapshotRepo()
        snapshots.save(make_snapshot("TCS", T1, 100.0, 1))
        snapshots.save(make_snapshot("TCS", T2, 110.0, 2))
        signals = FakeChangeSignalRepo()
        signals.save(make_signal("TCS", T2, SignificanceTier.SIGNIFICANT, current_sid=2))

        svc = service_for_user("carol", snapshots=snapshots, signals=signals)

        feed = svc.get_feed("carol")
        assert len(feed.changes) == 1


class TestVisibility:
    def test_critical_is_always_ranked_first(self):
        instruments = FakeInstrumentRepo()
        instruments.add(build_instrument("TCS", "TCS.NS", "Tata Consultancy"))
        instruments.add(build_instrument("INFY", "INFY.NS", "Infosys"))

        snapshots = FakeMarketSnapshotRepo()
        snapshots.save(make_snapshot("TCS", T1, 100.0, 1))
        snapshots.save(make_snapshot("TCS", T2, 110.0, 2))
        snapshots.save(make_snapshot("INFY", T1, 200.0, 3))
        snapshots.save(make_snapshot("INFY", T2, 220.0, 4))
        signals = FakeChangeSignalRepo()
        signals.save(make_signal("INFY", T2, SignificanceTier.NOTABLE, current_sid=4))
        signals.save(make_signal("TCS", T2, SignificanceTier.CRITICAL, current_sid=2))

        watchlists = FakeWatchlistRepo(instruments)
        watchlists.add_item("default-user", "TCS")
        watchlists.add_item("default-user", "INFY")

        svc = build_service(
            snapshots=snapshots, signals=signals, watchlists=watchlists, instruments=instruments
        )
        feed = svc.get_feed("default-user")
        assert len(feed.changes) == 2
        # CRITICAL always sorts before NOTABLE.
        assert feed.changes[0].significance is SignificanceTier.CRITICAL
        assert feed.changes[0].instrument_id == "TCS"


class TestProviderStatus:
    def test_no_snapshots_reports_unavailable(self):
        svc = build_service()
        feed = svc.get_feed("default-user")
        assert feed.provider_status is not None
        assert feed.provider_status.value == "UNAVAILABLE"

    def test_stale_only_reports_degraded(self):
        instruments = FakeInstrumentRepo()
        instruments.add(build_instrument())
        snapshots = FakeMarketSnapshotRepo()
        stale = make_snapshot("TCS", T2, 110.0, 2)
        stale = MarketSnapshot(**{**stale.__dict__, "data_status": DataStatus.STALE})
        snapshots._rows[2] = stale

        watchlists = FakeWatchlistRepo(instruments)
        watchlists.add_item("default-user", "TCS")

        svc = build_service(snapshots=snapshots, watchlists=watchlists, instruments=instruments)
        feed = svc.get_feed("default-user")
        assert feed.provider_status.value == "DEGRADED"


class TestCatchupWindow:
    def test_later_normal_signal_does_not_erase_earlier_significant(self):
        """Regression: last saw A -> significant B -> normal C -> return => B surfaces."""
        snapshots = FakeMarketSnapshotRepo()
        snapshots.save(make_snapshot("TCS", T0, 100.0, 1))  # A
        snapshots.save(make_snapshot("TCS", T1, 110.0, 2))  # B (big move)
        snapshots.save(make_snapshot("TCS", T2, 111.0, 3))  # C (normal tick)

        signals = FakeChangeSignalRepo()
        signals.save(make_signal("TCS", T1, SignificanceTier.SIGNIFICANT, current_sid=2, desc="B"))
        signals.save(make_signal("TCS", T2, SignificanceTier.NORMAL, current_sid=3, desc="C"))

        last_seen = FakeUserLastSeenRepo()
        # User last checked when they saw snapshot A.
        last_seen.upsert(UserLastSeen(user_id="default-user", instrument_id="TCS",
                                      last_seen_at=T0, last_seen_snapshot_id=1))

        svc = service_for_user("default-user", snapshots=snapshots, signals=signals, last_seen=last_seen)

        feed = svc.get_feed("default-user")
        # The significant B must still surface even though a later NORMAL C exists.
        assert len(feed.changes) == 1
        assert feed.changes[0].event_description == "B"
        assert feed.changes[0].significance is SignificanceTier.SIGNIFICANT

        # Detail view exposes the auditable meaningful list (B), never just C.
        detail = svc.get_instrument_change("default-user", "TCS")
        assert detail.latest_signal is not None
        assert detail.latest_signal.event_description == "B"
        assert [s.event_description for s in detail.other_signals] == []

    def test_consolidation_picks_highest_tier_then_largest_move(self):
        snapshots = FakeMarketSnapshotRepo()
        snapshots.save(make_snapshot("TCS", T0, 100.0, 1))
        snapshots.save(make_snapshot("TCS", T1, 104.0, 2))
        snapshots.save(make_snapshot("TCS", T2, 108.0, 3))

        signals = FakeChangeSignalRepo()
        signals.save(make_signal("TCS", T1, SignificanceTier.NOTABLE, current_sid=2, desc="notable"))
        signals.save(make_signal("TCS", T2, SignificanceTier.CRITICAL, current_sid=3, desc="critical"))

        svc = service_for_user("default-user", snapshots=snapshots, signals=signals)
        feed = svc.get_feed("default-user")
        assert len(feed.changes) == 1
        assert feed.changes[0].event_description == "critical"


def test_mark_seen_advances_last_seen_for_all_instruments():
    instruments = FakeInstrumentRepo()
    instruments.add(build_instrument("TCS", "TCS.NS", "Tata"))
    instruments.add(build_instrument("INFY", "INFY.NS", "Infosys"))
    snapshots = FakeMarketSnapshotRepo()
    snapshots.save(make_snapshot("TCS", T2, 110.0, 2))
    snapshots.save(make_snapshot("INFY", T2, 220.0, 4))
    watchlists = FakeWatchlistRepo(instruments)
    watchlists.add_item("default-user", "TCS")
    watchlists.add_item("default-user", "INFY")
    last_seen = FakeUserLastSeenRepo()

    svc = build_service(
        snapshots=snapshots, watchlists=watchlists, last_seen=last_seen, instruments=instruments
    )
    svc.mark_seen("default-user")

    assert last_seen.get("default-user", "TCS") is not None
    assert last_seen.get("default-user", "INFY") is not None


def test_mark_seen_uses_delivered_snapshot_watermark_not_newer_snapshot():
    instruments = FakeInstrumentRepo()
    instruments.add(build_instrument())
    snapshots = FakeMarketSnapshotRepo()
    snapshots.save(make_snapshot("TCS", T1, 105.0, 2))
    snapshots.save(make_snapshot("TCS", T2, 110.0, 3))
    watchlists = FakeWatchlistRepo(instruments)
    watchlists.add_item("default-user", "TCS")
    last_seen = FakeUserLastSeenRepo()
    svc = build_service(
        snapshots=snapshots,
        watchlists=watchlists,
        last_seen=last_seen,
        instruments=instruments,
    )

    # The feed delivered snapshot 2; snapshot 3 arrived before the ack.
    svc.mark_seen("default-user", snapshot_ids={"TCS": 2})

    assert last_seen.get("default-user", "TCS").last_seen_snapshot_id == 2


class TestPerInstrumentMarketStatus:
    """Spec §16: the stock detail carries the instrument's OWN exchange status,
    never the feed's global one. Wired to the exchange-aware clock."""

    def test_detail_uses_instrument_exchange(self, monkeypatch):
        instruments = FakeInstrumentRepo()
        instruments.add(build_instrument("AMD", "AMD", "Advanced Micro Devices", exchange="NASDAQ"))
        snapshots = FakeMarketSnapshotRepo()
        snapshots.save(make_snapshot("AMD", T1, 150.0, 1))
        watchlists = FakeWatchlistRepo(instruments)
        watchlists.add_item("sel", "AMD")
        svc = build_service(
            snapshots=snapshots,
            watchlists=watchlists,
            instruments=instruments,
        )

        seen = {}

        def fake_market_status(observed_at, *, exchange=None, **kwargs):
            seen["exchange"] = exchange
            seen["observed"] = observed_at
            return MarketStatus.CLOSED

        monkeypatch.setattr(
            "app.application.catchup_service.market_status", fake_market_status
        )
        detail = svc.get_instrument_change("sel", "AMD")

        assert seen.get("exchange") == "NASDAQ"
        assert seen.get("observed") is not None
        assert detail.market_status is MarketStatus.CLOSED

    def test_market_status_is_unknown_without_snapshot(self):
        instruments = FakeInstrumentRepo()
        instruments.add(build_instrument("AMD", "AMD", "Advanced Micro Devices", exchange="NASDAQ"))
        watchlists = FakeWatchlistRepo(instruments)
        watchlists.add_item("sel", "AMD")
        svc = build_service(watchlists=watchlists, instruments=instruments)

        detail = svc.get_instrument_change("sel", "AMD")

        assert detail.market_status is MarketStatus.UNKNOWN


class TestNewUserStartsEmpty:
    def test_fresh_user_watchlist_is_empty(self):
        instruments = FakeInstrumentRepo()
        watchlists = FakeWatchlistRepo(instruments)
        svc = build_service(watchlists=watchlists, instruments=instruments)

        feed = svc.get_feed("brand-new-user")

        # No pre-populated stocks, no fabricated changes, no personalisation.
        assert watchlists.get_items("brand-new-user").items == []
        assert feed.changes == []
        assert feed.user_relevance is None
        assert feed.acknowledgement == {}
