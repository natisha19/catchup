"""Ingestion service tests.

Use an in-memory fake provider and fake repositories to verify the full
ingestion pipeline without any network or database.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.analytics.thresholds import SignificanceThresholds
from app.application.ingestion_service import IngestionService
from app.domain.entities import CorporateEvent
from app.domain.enums import (
    CorporateEventStatus,
    CorporateEventType,
    DataStatus,
    ProviderFailure,
    SignificanceTier,
)
from app.market_data.data_types import (
    HistoricalData,
    MarketSnapshotCandidate,
)
from tests.fakes import (
    FakeChangeSignalRepo,
    FakeCorporateEventRepo,
    FakeInstrumentRepo,
    FakeMarketSnapshotRepo,
    FakeProvider,
    build_instrument,
    build_snapshot,
)


def build_service(provider, instruments, snapshots=None, events=None, signals=None):
    return IngestionService(
        provider=provider,
        instruments=instruments,
        snapshots=snapshots or FakeMarketSnapshotRepo(),
        events=events or FakeCorporateEventRepo(),
        signals=signals or FakeChangeSignalRepo(),
        thresholds=SignificanceThresholds.defaults(),
        baseline_window_days=30,
        min_baseline_returns=20,
        limited_baseline_returns=5,
    )


def make_candidate(price, volume, observed_at=None):
    return MarketSnapshotCandidate(
        observed_at=observed_at or datetime.now(timezone.utc),
        price=price,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=volume,
        currency="INR",
    )


class TestIngestionHappyPath:
    def test_persists_snapshot_and_signal(self):
        instruments = FakeInstrumentRepo()
        inst = build_instrument()
        instruments.add(inst)
        snapshots = FakeMarketSnapshotRepo()
        signals = FakeChangeSignalRepo()

        # Seed a prior snapshot so the diff has a `previous`.
        prior = build_snapshot("TCS", datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0)
        snapshots.save(prior)

        provider = FakeProvider(
            snapshots={"TCS": make_candidate(103.0, 50_000)},
        )
        svc = build_service(provider, instruments, snapshots=snapshots, signals=signals)

        result = svc.ingest(["TCS"])

        assert result.snapshots == 1
        assert result.signals == 1
        assert result.instruments == 1
        assert result.provider_failures == 0
        latest = snapshots.get_latest("TCS")
        assert latest is not None and latest.price == 103.0
        sig = signals.get_latest("TCS")
        assert sig is not None
        assert sig.instrument_id == "TCS"


class TestProviderFailure:
    def test_marks_last_valid_snapshot_stale(self):
        instruments = FakeInstrumentRepo()
        inst = build_instrument()
        instruments.add(inst)
        snapshots = FakeMarketSnapshotRepo()
        live = build_snapshot("TCS", datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0)
        snapshots.save(live)

        provider = FakeProvider(snapshot_failure=ProviderFailure.NETWORK)
        svc = build_service(provider, instruments, snapshots=snapshots)

        result = svc.ingest(["TCS"])

        assert result.provider_failures == 1
        assert result.signals == 0
        latest = snapshots.get_latest("TCS")
        assert latest is not None
        assert latest.data_status is DataStatus.STALE


class TestNoData:
    def test_no_data_produces_no_snapshot_and_no_signal(self):
        instruments = FakeInstrumentRepo()
        inst = build_instrument()
        instruments.add(inst)
        snapshots = FakeMarketSnapshotRepo()
        signals = FakeChangeSignalRepo()

        provider = FakeProvider(snapshot_failure=ProviderFailure.EMPTY)
        svc = build_service(provider, instruments, snapshots=snapshots, signals=signals)

        result = svc.ingest(["TCS"])

        assert result.provider_failures == 1
        assert snapshots.count_for_instrument("TCS") == 0
        assert signals.get_latest("TCS") is None


class TestCorporateEvent:
    def test_merger_signal_is_critical(self):
        instruments = FakeInstrumentRepo()
        inst = build_instrument()
        instruments.add(inst)
        snapshots = FakeMarketSnapshotRepo()
        prior = build_snapshot("TCS", datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0)
        snapshots.save(prior)
        events = FakeCorporateEventRepo()
        signals = FakeChangeSignalRepo()

        event = CorporateEvent(
            instrument_id="TCS",
            event_type=CorporateEventType.MERGER_ACQUISITION,
            event_time=datetime.now(timezone.utc),
            description="Acquisition",
            source="fake",
            status=CorporateEventStatus.CONFIRMED,
        )
        provider = FakeProvider(
            snapshots={"TCS": make_candidate(101.0, 20_000)},
            events=[event],
        )
        svc = build_service(provider, instruments, snapshots=snapshots, events=events, signals=signals)

        svc.ingest(["TCS"])

        sig = signals.get_latest("TCS")
        assert sig is not None
        assert sig.significance is SignificanceTier.CRITICAL
        assert "MERGER_ACQUISITION_EVENT" in sig.reason_codes
        assert sig.event_description == "Merger or acquisition"
        assert len(events._rows) == 1


class TestIdempotency:
    def test_reingesting_same_observation_does_not_duplicate_rows(self):
        instruments = FakeInstrumentRepo()
        inst = build_instrument()
        instruments.add(inst)
        snapshots = FakeMarketSnapshotRepo()
        signals = FakeChangeSignalRepo()

        observed = datetime(2024, 2, 1, tzinfo=timezone.utc)
        provider = FakeProvider(
            snapshots={"TCS": make_candidate(105.0, 30_000, observed_at=observed)},
        )
        svc = build_service(provider, instruments, snapshots=snapshots, signals=signals)

        svc.ingest(["TCS"])
        svc.ingest(["TCS"])

        assert snapshots.count_for_instrument("TCS") == 1
        assert len([s for s in signals._rows if s.instrument_id == "TCS"]) == 1
