"""Ingestion service.

Runs independently of user requests. For each active instrument:
fetch market data -> validate -> normalize -> persist snapshot (dedup) ->
compute change signal -> persist signal.

The pass is split into two phases so freshness and enrichment behave differently:

* ``quote`` (fast): fetch + persist current snapshots for every instrument under
  bounded concurrency. Network fetches run in a small thread pool; DB writes are
  serialized on the caller's session (a SQLAlchemy Session is not thread-safe).
  No history, no events — this phase must complete quickly so quotes stay fresh.
* ``enrich`` (slow): refresh the baseline history + corporate events and turn the
  persisted snapshots into ChangeSignals. Runs on a slower cadence (the worker
  rate-limits it), so the provider is not hammered on every tick.

Depends only on the MarketDataProvider abstraction and repository interfaces.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.analytics.baseline import compute_baseline
from app.analytics.change_detector import ChangeEvidence, classify_change
from app.analytics.thresholds import SignificanceThresholds
from app.domain.entities import CorporateEvent, Instrument, MarketSnapshot
from app.domain.enums import DataStatus, ProviderFailure
from app.domain.interfaces.repositories import (
    ChangeSignalRepository,
    CorporateEventRepository,
    InstrumentRepository,
    MarketSnapshotRepository,
)
from app.market_data.data_types import MarketSnapshotCandidate, ProviderResult
from app.market_data.normalizer import normalize_snapshot
from app.market_data.provider import MarketDataProvider
from app.market_data.validator import InvalidObservation

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        provider: MarketDataProvider,
        instruments: InstrumentRepository,
        snapshots: MarketSnapshotRepository,
        events: CorporateEventRepository,
        signals: ChangeSignalRepository,
        thresholds: SignificanceThresholds,
        baseline_window_days: int,
        min_baseline_returns: int,
        limited_baseline_returns: int,
        delayed_threshold_minutes: int = 5,
        stale_threshold_minutes: int = 30,
        quote_workers: int = 4,
    ) -> None:
        self._provider = provider
        self._instruments = instruments
        self._snapshots = snapshots
        self._events = events
        self._signals = signals
        self._thresholds = thresholds
        self._baseline_window_days = baseline_window_days
        self._min_baseline_returns = min_baseline_returns
        self._limited_baseline_returns = limited_baseline_returns
        self._delayed_threshold_minutes = delayed_threshold_minutes
        self._stale_threshold_minutes = stale_threshold_minutes
        self._quote_workers = max(1, quote_workers)

    def ingest(self, instrument_ids: list[str] | None = None) -> IngestionResult:
        """Full bootstrap pass: fast quotes + slow enrichment in one unit.

        Kept for one-off seeding and tests; the periodic worker calls
        ``quote`` / ``enrich`` separately so each phase can run on its own cadence.
        """
        instruments = self._resolve_instruments(instrument_ids)
        result = IngestionResult()
        result.instruments = len(instruments)
        fresh_ids = self._fetch_and_persist_quotes(instruments, result)
        self._enrich_instruments(instruments, result, fresh_ids=fresh_ids)
        return result

    def quote(self, instrument_ids: list[str] | None = None) -> IngestionResult:
        """Fast phase: fetch + persist snapshots (bounded concurrency), no signals.

        The provider is the throughput bottleneck, so fetches run in a thread
        pool; persistence is serialized so the injected repos/session stay safe.
        """
        instruments = self._resolve_instruments(instrument_ids)
        result = IngestionResult()
        result.instruments = len(instruments)
        self._fetch_and_persist_quotes(instruments, result)
        return result

    def enrich(self, instrument_ids: list[str] | None = None) -> IngestionResult:
        """Slow phase: baseline history + corporate events -> ChangeSignals.

        Requires snapshots to already be persisted (by ``quote`` or a prior run).
        Runs on a slower cadence to keep provider load bounded.
        """
        instruments = self._resolve_instruments(instrument_ids)
        result = IngestionResult()
        result.instruments = len(instruments)
        self._enrich_instruments(instruments, result, fresh_ids=None)
        return result

    def _resolve_instruments(self, instrument_ids: list[str] | None) -> list[Instrument]:
        if instrument_ids is not None:
            resolved = []
            for iid in instrument_ids:
                inst = self._instruments.get(iid)
                if inst:
                    resolved.append(inst)
            return resolved
        return self._instruments.list_active()

    def _fetch_and_persist_quotes(
        self, instruments: list[Instrument], result: IngestionResult
    ) -> set[str]:
        """Concurrent fetch + serial persist. Returns instrument_ids with a fresh quote."""
        outcomes = self._fetch_snapshots(instruments)
        fresh_ids: set[str] = set()
        source = self._provider.source_name()

        for instrument in instruments:
            outcome = outcomes[instrument.instrument_id]
            if not outcome.ok or outcome.value is None:
                self._handle_provider_failure(instrument, outcome.failure, source, result)
                continue
            try:
                status = self._data_status_for(outcome.value.observed_at)
                snapshot = normalize_snapshot(
                    instrument.instrument_id,
                    outcome.value,
                    source=source,
                    data_status=status,
                )
            except InvalidObservation as exc:
                logger.warning(
                    "invalid observation instrument=%s: %s", instrument.symbol, exc
                )
                result.invalid += 1
                continue
            self._snapshots.save(snapshot)
            result.snapshots += 1
            fresh_ids.add(instrument.instrument_id)

        return fresh_ids

    def _fetch_snapshots(
        self, instruments: list[Instrument],
    ) -> dict[str, ProviderResult[MarketSnapshotCandidate]]:
        """Bounded-concurrency provider fetch; per-instrument failure isolation."""
        outcomes: dict[str, ProviderResult[MarketSnapshotCandidate]] = {}
        if not instruments:
            return outcomes
        with ThreadPoolExecutor(max_workers=self._quote_workers) as executor:
            future_to_id = {
                executor.submit(self._provider.get_snapshot, inst): inst.instrument_id
                for inst in instruments
            }
            for future in as_completed(future_to_id):
                instrument_id = future_to_id[future]
                try:
                    outcomes[instrument_id] = future.result()
                except Exception as exc:  # noqa: BLE001 - isolate one bad ticker
                    logger.warning("quote fetch raised instrument=%s: %s", instrument_id, exc)
                    outcomes[instrument_id] = ProviderResult.failed(
                        ProviderFailure.UNKNOWN, f"quote fetch raised: {exc}"
                    )
        return outcomes

    def _enrich_instruments(
        self,
        instruments: list[Instrument],
        result: IngestionResult,
        fresh_ids: set[str] | None,
    ) -> None:
        for instrument in instruments:
            # A combined pass only classifies instruments whose quote just landed;
            # a standalone enrich() classifies whatever has a persisted snapshot.
            if fresh_ids is not None and instrument.instrument_id not in fresh_ids:
                continue

            snapshots = self._snapshots.history(instrument.instrument_id, limit=2)
            if not snapshots:
                # No snapshot yet (e.g. provider never returned data). Nothing to
                # classify; the signalled state stays authoritative elsewhere.
                continue
            current = snapshots[-1]
            previous = snapshots[-2] if len(snapshots) >= 2 else None
            self._classify_and_persist(instrument, previous, current, result)

    def _classify_and_persist(
        self,
        instrument: Instrument,
        previous: MarketSnapshot | None,
        current: MarketSnapshot,
        result: IngestionResult,
    ) -> None:
        # --- history / baseline evidence ------------------------------------
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self._baseline_window_days * 2)
        history_result = self._provider.get_historical_data(instrument, start, end)

        historical_returns: list[float] = []
        historical_volumes: list[float] = []
        if history_result.ok and history_result.value:
            prices = [h.price for h in history_result.value]
            for i in range(1, len(prices)):
                if prices[i - 1] and prices[i]:
                    historical_returns.append(
                        ((prices[i] / prices[i - 1]) - 1) * 100
                    )
            historical_volumes = [
                h.volume for h in history_result.value if h.volume is not None
            ]

        # --- corporate events ------------------------------------------------
        corporate_result = self._provider.get_corporate_events(instrument, start, end)
        corporate: list[CorporateEvent] = []
        if corporate_result.ok and corporate_result.value:
            # Persist every event for auditability/deduplication, but only
            # confirmed events can elevate an attention signal. A scheduled
            # earnings date is useful context, not evidence that it happened.
            persisted_events = [self._events.save(event) for event in corporate_result.value]
            corporate = [
                event
                for event in persisted_events
                if event.status.value == "CONFIRMED"
            ]

        evidence = ChangeEvidence(
            previous=previous,
            current=current,
            historical_returns=historical_returns,
            historical_volumes=historical_volumes,
            corporate_events=corporate,
        )

        signal = classify_change(
            evidence,
            thresholds=self._thresholds,
            baseline_calculator=lambda rets: compute_baseline(
                rets,
                min_returns=self._min_baseline_returns,
                limited_returns=self._limited_baseline_returns,
            ),
        )
        self._signals.save(signal)
        result.signals += 1
        logger.info(
            "signal instrument=%s tier=%s return=%.2f z=%s vol=%s",
            instrument.symbol,
            signal.significance.value,
            signal.return_pct or 0.0,
            signal.z_score,
            signal.volume_ratio,
        )

    def _handle_provider_failure(
        self,
        instrument: Instrument,
        failure: ProviderFailure | None,
        source: str,
        result: IngestionResult,
    ) -> None:
        latest = self._snapshots.get_latest(instrument.instrument_id)
        logger.warning(
            "provider failure instrument=%s failure=%s; latest=%s",
            instrument.symbol,
            failure,
            "yes" if latest else "no",
        )
        result.provider_failures += 1
        if latest is not None:
            # Keep last validated data but mark it stale for the consumer.
            self._snapshots.save(
                replace_status(latest, DataStatus.STALE)
            )

    def _data_status_for(self, observed_at: datetime) -> DataStatus:
        """Classify freshness from provider quote time, never ingestion time."""
        timestamp = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
        if age <= timedelta(minutes=self._delayed_threshold_minutes):
            return DataStatus.LIVE
        if age <= timedelta(minutes=self._stale_threshold_minutes):
            return DataStatus.DELAYED
        return DataStatus.STALE


class IngestionResult:
    def __init__(self) -> None:
        self.instruments = 0
        self.snapshots = 0
        self.signals = 0
        self.invalid = 0
        self.provider_failures = 0


def replace_status(snapshot, status: DataStatus):
    return replace(snapshot, data_status=status)