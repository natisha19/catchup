"""Ingestion service.

Runs independently of user requests. For each active instrument:
fetch market data -> validate -> normalize -> persist snapshot (dedup) ->
compute change signal -> persist signal.

Depends only on the MarketDataProvider abstraction and repository interfaces.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.analytics.baseline import compute_baseline
from app.analytics.change_detector import ChangeEvidence, classify_change
from app.analytics.thresholds import SignificanceThresholds
from app.domain.entities import Instrument
from app.domain.enums import DataStatus, ProviderFailure
from app.domain.interfaces.repositories import (
    ChangeSignalRepository,
    CorporateEventRepository,
    InstrumentRepository,
    MarketSnapshotRepository,
)
from app.market_data.data_types import MarketSnapshotCandidate
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

    def ingest(self, instrument_ids: list[str] | None = None) -> IngestionResult:
        """Run one ingestion pass. Returns summary counts for observability."""
        instruments = self._resolve_instruments(instrument_ids)
        result = IngestionResult()
        result.instruments = len(instruments)

        for instrument in instruments:
            self._ingest_one(instrument, result)

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

    def _ingest_one(self, instrument: Instrument, result: IngestionResult) -> None:
        source = self._provider.source_name()

        # --- snapshot -------------------------------------------------------
        snap_result = self._provider.get_snapshot(instrument)
        if not snap_result.ok or snap_result.value is None:
            self._handle_provider_failure(instrument, snap_result.failure, source, result)
            return

        candidate = snap_result.value
        try:
            status = self._data_status_for(candidate.observed_at)
            snapshot = normalize_snapshot(
                instrument.instrument_id,
                candidate,
                source=source,
                data_status=status,
            )
        except InvalidObservation as exc:
            logger.warning(
                "invalid observation instrument=%s: %s", instrument.symbol, exc
            )
            result.invalid += 1
            return

        # Capture the previous validated snapshot BEFORE persisting the new one
        # so the diff compares the current observation against the prior state.
        previous = self._snapshots.get_latest(instrument.instrument_id)
        persisted = self._snapshots.save(snapshot)
        result.snapshots += 1

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
        corporate = []
        if corporate_result.ok and corporate_result.value:
            # Persist every event for auditability/deduplication, but only
            # confirmed events can elevate an attention signal. A scheduled
            # earnings date is useful context, not evidence that it happened.
            persisted_events = [self._events.save(event) for event in corporate_result.value]
            corporate = [
                event for event in persisted_events
                if event.status.value == "CONFIRMED"
            ]

        evidence = ChangeEvidence(
            previous=previous,
            current=persisted,
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
