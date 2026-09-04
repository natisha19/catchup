"""ChangeDetector.

Replaces per-observation logic that turns a current snapshot + historical
evidence + corporate events into a ChangeSignal. This is a replaceable unit
(spec §56) so the baseline/anomaly/significance strategy can evolve without an
API redesign.

Dependencies are injected (baseline calculator, thresholds, signature) keeping
this testable in isolation from any database or provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.analytics import anomaly, returns, volume
from app.analytics.baseline import Baseline
from app.analytics.significance import (
    Classification,
    SignificanceThresholds,
    classify_corporate,
    classify_price,
    classify_volume,
    combine,
)
from app.domain.entities import ChangeSignal, CorporateEvent, MarketSnapshot
from app.domain.enums import ChangeEventType, SignificanceTier

ReasonCodes = list[str]
BaselineCalculator = Callable[[list[float]], Baseline]


@dataclass(frozen=True)
class ChangeEvidence:
    """All inputs needed to classify a single instrument's change."""

    previous: MarketSnapshot | None
    current: MarketSnapshot
    historical_returns: list[float]
    historical_volumes: list[float]
    corporate_events: list[CorporateEvent]


def classify_change(
    evidence: ChangeEvidence,
    *,
    thresholds: SignificanceThresholds,
    baseline_calculator: BaselineCalculator,
) -> ChangeSignal:
    current = evidence.current
    previous = evidence.previous

    # --- current return vs previous state -------------------------------
    current_price = current.price
    previous_price = previous.price if previous is not None else None
    return_pct = None
    if current_price is not None and previous_price is not None and previous_price > 0:
        return_pct = returns.percent_return(previous_price, current_price)

    # --- baseline (never includes the current return) --------------------
    baseline = baseline_calculator(evidence.historical_returns)
    z = anomaly.z_score(return_pct, baseline.mean, baseline.std)

    # --- volume ----------------------------------------------------------
    avg_volume = volume.average_volume(evidence.historical_volumes)
    vol_ratio = volume.volume_ratio(current.volume, avg_volume if avg_volume > 0 else None)

    # --- classifications --------------------------------------------------
    price_cls = classify_price(z=z, return_pct=return_pct, thresholds=thresholds)
    volume_cls = classify_volume(volume_ratio=vol_ratio, thresholds=thresholds)

    corporate_cls: list[Classification] = []
    has_corporate = False
    for ev in evidence.corporate_events:
        cls = classify_corporate(ev.event_type)
        if cls is not None:
            corporate_cls.append(cls)
            has_corporate = True

    combined = combine(price_cls, [volume_cls, *corporate_cls])

    # Conservative fallback: without any evidence the change is NORMAL until we
    # have enough history to say otherwise.
    if baseline.status.value == "UNAVAILABLE" and return_pct is not None and combined.tier is SignificanceTier.NORMAL:
        combined = Classification(
            tier=SignificanceTier.NORMAL,
            reason_codes=combined.reason_codes,
            event_type=combined.event_type,
            event_description=combined.event_description or "",
        )

    event_desc = combined.event_description or _default_description(combined.event_type, has_corporate)

    if combined.tier is SignificanceTier.NORMAL and not reason_worthy(combined):
        event_desc = "No meaningful change detected"

    return ChangeSignal(
        instrument_id=current.instrument_id,
        observed_at=current.observed_at,
        previous_snapshot_id=previous.id if previous else None,
        current_snapshot_id=current.id if current else None,
        event_type=combined.event_type,
        previous_price=previous_price,
        current_price=current_price,
        return_pct=return_pct,
        baseline_mean=baseline.mean,
        baseline_std=baseline.std,
        z_score=z,
        current_volume=current.volume,
        baseline_average_volume=avg_volume if avg_volume > 0 else None,
        volume_ratio=vol_ratio,
        significance=combined.tier,
        reason_codes=combined.reason_codes,
        data_status=current.data_status,
        event_description=event_desc,
    )


def reason_worthy(cls: Classification) -> bool:
    return bool(cls.reason_codes)


def _default_description(event_type: ChangeEventType, has_corporate: bool) -> str:
    if has_corporate:
        return "Corporate event"
    if event_type is ChangeEventType.VOLUME_ANOMALY:
        return "Trading volume increased"
    if event_type is ChangeEventType.PRICE_ANOMALY:
        return "Unusual price movement"
    return "Market change"
