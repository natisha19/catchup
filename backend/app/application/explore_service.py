"""Explore service — real discovery data for the Home page.

Home is "I don't know what to watch yet" (spec §1–§3). It must surface real
movers, dippers and unusual activity, so the data comes from the latest
persisted snapshots + signals of the curated DISCOVERY universe — instruments
the ingestion worker keeps fresh regardless of any user's watchlist. Nothing
here fabricates a number; sections are populated only from instruments that
actually have observed data.

Signals are computed at ingestion time (baseline history + corporate events),
so the service is a pure read-side query — no provider calls, no derivation.
"""

from __future__ import annotations

from app.domain.entities import (
    ExploreItem,
    ExploreSections,
    Instrument,
)
from app.domain.interfaces.repositories import (
    ChangeSignalRepository,
    InstrumentRepository,
    MarketSnapshotRepository,
)
from app.market_data.catalog import InstrumentCatalog


class ExploreService:
    def __init__(
        self,
        instruments: InstrumentRepository,
        snapshots: MarketSnapshotRepository,
        signals: ChangeSignalRepository,
        catalog: InstrumentCatalog | None = None,
    ) -> None:
        self._instruments = instruments
        self._snapshots = snapshots
        self._signals = signals
        self._catalog = catalog

    def sections(self, limit: int = 6, sector: str | None = None) -> ExploreSections:
        """Movers / dippers / unusual + by-sector breadcrumbs from real data.

        ``sector`` is not a post-hoc client-side filter: it scopes the
        underlying discovery query so every section is computed from exactly the
        instruments in that sector. The ``sectors`` breadcrumbs always list the
        full discovery universe so the filter chips remain stable; if the sector
        genuinely has no valid observations it simply yields empty sections
        (honest "no data", never fabricated ranks).
        """
        ids = self._discovery_ids()
        instruments = [
            inst
            for inst in (self._instruments.get(iid) for iid in ids)
            if inst is not None
        ]
        if not instruments:
            return ExploreSections(movers=[], dippers=[], unusual=[], sectors=[])

        sector_filtered = [
            inst
            for inst in instruments
            if sector is None or (inst.sector or "").lower() == sector.lower()
        ]
        if not sector_filtered:
            return ExploreSections(
                movers=[],
                dippers=[],
                unusual=[],
                sectors=self._distinct_sectors(instruments),
            )

        ids_with_rows = [inst.instrument_id for inst in sector_filtered]
        snapshots = self._snapshots.get_latest_for(ids_with_rows)
        signals = self._signals.get_for_instruments(ids_with_rows)

        items: list[ExploreItem] = []
        for inst in sector_filtered:
            snap = snapshots.get(inst.instrument_id)
            signal = signals.get(inst.instrument_id)
            if snap is None or signal is None:
                # Awaiting first data / baseline. Never fabricate a ranking.
                continue
            items.append(ExploreItem(instrument=inst, snapshot=snap, signal=signal))

        movers = sorted(
            (i for i in items if i.signal.return_pct is not None and i.signal.return_pct > 0),
            key=lambda i: i.signal.return_pct or 0.0,
            reverse=True,
        )[:limit]

        dippers = sorted(
            (i for i in items if i.signal.return_pct is not None and i.signal.return_pct < 0),
            key=lambda i: i.signal.return_pct or 0.0,
        )[:limit]

        def _unusualness(item: ExploreItem) -> float:
            signal = item.signal
            z = abs(signal.z_score) if signal.z_score is not None else -1.0
            v = signal.volume_ratio if signal.volume_ratio is not None else 0.0
            return z + v

        unusual = sorted(
            (
                i
                for i in items
                if (i.signal.z_score is not None or i.signal.volume_ratio is not None)
            ),
            key=_unusualness,
            reverse=True,
        )[:limit]

        sectors = sorted(
            {
                inst.sector
                for inst in instruments
                if inst.sector
            }
        )

        return ExploreSections(
            movers=movers,
            dippers=dippers,
            unusual=unusual,
            sectors=sectors,
        )

    def _distinct_sectors(self, instruments: list[Instrument]) -> list[str]:
        return sorted({inst.sector for inst in instruments if inst.sector})

    def _discovery_ids(self) -> list[str]:
        if self._catalog is None:
            return []
        return sorted(
            inst.instrument_id
            for inst in self._catalog.discovery_instruments()
            if inst.instrument_id
        )