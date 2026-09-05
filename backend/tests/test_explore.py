"""Explore service + personalization tests.

Explore must surface REAL movers/dippers/unusual activity from persisted
snapshots + signals of the discovery universe — never fabricated ranks, and
nothing while a brand-new user / empty universe is still awaiting data.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.application.explore_service import ExploreService
from app.application.personalization import watchlist_composition
from app.domain.entities import ChangeSignal
from app.domain.enums import ChangeEventType, DataStatus, SignificanceTier
from app.market_data.catalog import default_catalog
from tests.fakes import (
    FakeChangeSignalRepo,
    FakeInstrumentRepo,
    FakeMarketSnapshotRepo,
    build_instrument,
)
from tests.test_catchup import make_snapshot


def build_service(instruments, snapshots=None, signals=None):
    return ExploreService(
        instruments=instruments,
        snapshots=snapshots or FakeMarketSnapshotRepo(),
        signals=signals or FakeChangeSignalRepo(),
        catalog=default_catalog(),
    )


def _signal(iid, now, ret, z, vol):
    return ChangeSignal(
        instrument_id=iid,
        observed_at=now,
        previous_snapshot_id=1,
        current_snapshot_id=2,
        event_type=ChangeEventType.PRICE_ANOMALY,
        previous_price=100.0,
        current_price=round(100 * (1 + ret / 100), 2),
        return_pct=ret,
        baseline_mean=0.0,
        baseline_std=2.0,
        z_score=z,
        current_volume=1000.0,
        baseline_average_volume=500.0,
        volume_ratio=vol,
        significance=SignificanceTier.SIGNIFICANT,
        reason_codes=["SIGNIFICANT_PRICE_MOVE"],
        data_status=DataStatus.LIVE,
        event_description="X",
    )


def seed(rows: dict[str, tuple[str, float, float, float | None]]):
    """Rows: instrument_id -> (sector, return_pct, z, volume). Returns repos."""
    instruments = FakeInstrumentRepo()
    snapshots = FakeMarketSnapshotRepo()
    signals = FakeChangeSignalRepo()
    now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
    sid = 0
    for iid, (sector, ret, z, vol) in rows.items():
        sid += 1
        instruments.add(build_instrument(iid, iid, f"{iid} Co", sector=sector))
        snapshots.save(make_snapshot(iid, now, 100.0, sid))
        signals.save(_signal(iid, now, ret, z, vol))
    return instruments, snapshots, signals


class TestExploreSections:
    def test_no_rows_yields_empty_sections(self):
        instruments = FakeInstrumentRepo()
        sections = build_service(instruments).sections()
        assert sections.movers == []
        assert sections.dippers == []
        assert sections.unusual == []
        assert sections.sectors == []

    def test_movers_dippers_unusual_rank_from_real_data(self):
        rows = {
            "TCS": ("IT", 5.0, 2.0, 1.2),
            "INFY": ("IT", -3.5, -1.5, 0.8),
            "RELIANCE": ("Energy", 8.0, 3.0, 2.5),
            "SBIN": ("Financials", 1.0, 0.5, 0.4),
            "ITC": ("Consumer Staples", -6.0, -2.0, 1.1),
        }
        instruments, snapshots, signals = seed(rows)
        sections = build_service(instruments, snapshots, signals).sections(limit=2)

        assert [i.instrument.instrument_id for i in sections.movers] == ["RELIANCE", "TCS"]
        assert [i.instrument.instrument_id for i in sections.dippers] == ["ITC", "INFY"]
        # Unusual = |z| + volume, desc: RELIANCE (3.0+2.5=5.5), TCS (2.0+1.2=3.2).
        assert [i.instrument.instrument_id for i in sections.unusual][:2] == ["RELIANCE", "TCS"]

    def test_awaiting_baseline_instruments_are_excluded(self):
        instruments, snapshots, signals = seed({"TCS": ("IT", 5.0, 2.0, 1.2)})
        # INFY has a snapshot but no signal yet — never ranked, never fabricated.
        instruments.add(build_instrument("INFY", "INFY", "Infosys", sector="IT"))
        snapshots.save(make_snapshot("INFY", datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc), 100.0, 99))
        sections = build_service(instruments, snapshots, signals).sections()
        ids = {
            i.instrument.instrument_id
            for group in (sections.movers, sections.dippers, sections.unusual)
            for i in group
        }
        assert "INFY" not in ids

    def test_sectors_are_distinct_and_sorted(self):
        instruments, snapshots, signals = seed({"TCS": ("IT", 5.0, 2.0, 1.2)})
        instruments.add(build_instrument("SBIN", "SBIN", "SBI", sector="Financials"))
        sections = build_service(instruments, snapshots, signals).sections()
        assert sections.sectors == ["Financials", "IT"]


class TestExploreSectorFilter:
    """The selected sector must genuinely scope the underlying query, not be a
    client-side filter over already-fetched rows."""

    def test_sector_scopes_movers_dippers_unusual(self):
        rows = {
            "TCS": ("IT", 5.0, 2.0, 1.2),
            "INFY": ("IT", -3.5, -1.5, 0.8),
            "RELIANCE": ("Energy", 8.0, 3.0, 2.5),
            "SBIN": ("Financials", 1.0, 0.5, 0.4),
        }
        instruments, snapshots, signals = seed(rows)

        sections = build_service(instruments, snapshots, signals).sections(limit=10, sector="IT")

        movers = {i.instrument.instrument_id for i in sections.movers}
        dippers = {i.instrument.instrument_id for i in sections.dippers}
        unusual = {i.instrument.instrument_id for i in sections.unusual}
        assert movers == {"TCS"}
        assert dippers == {"INFY"}
        assert unusual <= {"TCS", "INFY"}
        # Breadcrumbs stay the stable full-discovery list for the chips.
        assert sections.sectors == ["Energy", "Financials", "IT"]

    def test_sector_match_is_case_insensitive(self):
        instruments, snapshots, signals = seed({"TCS": ("IT", 5.0, 2.0, 1.2)})
        sections = build_service(instruments, snapshots, signals).sections(sector="it")
        assert [i.instrument.instrument_id for i in sections.movers] == ["TCS"]

    def test_no_valid_observations_yields_honest_empty_but_keeps_chips(self):
        """A sector with instruments but no valid data must be empty — while
        the chips still list it, so 'no data' reads differently from 'no
        implementation'."""
        instruments, snapshots, signals = seed({"TCS": ("IT", 5.0, 2.0, 1.2)})
        # SBIN is discovery + persisted, but has neither snapshot nor signal.
        instruments.add(build_instrument("SBIN", "SBIN", "SBI", sector="Financials"))
        repo = build_service(instruments, snapshots, signals)

        sections = repo.sections(sector="Financials")

        assert sections.movers == []
        assert sections.dippers == []
        assert sections.unusual == []
        assert sections.sectors == ["Financials", "IT"]

    def test_unknown_sector_is_empty_and_chips_stable(self):
        instruments, snapshots, signals = seed({"TCS": ("IT", 5.0, 2.0, 1.2)})
        sections = build_service(instruments, snapshots, signals).sections(sector="NoSuch")
        assert sections.movers == []
        assert sections.sectors == ["IT"]


class TestWatchlistComposition:
    def test_cold_start_is_none(self):
        assert watchlist_composition([]) is None
        one = [build_instrument(sector="IT")]
        assert watchlist_composition(one) is None
        two = [
            build_instrument(sector="IT"),
            build_instrument("T2", "T2", "Two", sector="Financials"),
        ]
        assert watchlist_composition(two) is None

    def test_no_sector_data_is_none(self):
        insts = [
            build_instrument(sector=None),
            build_instrument("B", "B", "B Co", sector=None),
            build_instrument("C", "C", "C Co", sector=None),
        ]
        assert watchlist_composition(insts) is None

    def test_summary_derived_from_real_sectors(self):
        insts = [
            build_instrument(sector="IT"),
            build_instrument("B", "B", "B Co", sector="IT"),
            build_instrument("C", "C", "C Co", sector="Financials"),
            build_instrument("D", "D", "D Co", sector="IT"),
        ]
        result = watchlist_composition(insts)
        assert result is not None
        assert "IT" in result.summary
        assert "3 of 4" in result.summary