"""Significance classification.

Deterministic, configurable rules that combine price anomalies, return
magnitude, volume anomalies and corporate events into an objective
significance tier with human-readable reason codes.

Rules (spec §21, §20, §23):
- NORMAL     : absent any notable trigger
- NOTABLE    : abs_z >= Z_NOTABLE OR abs(return) >= RETURN_NOTABLE OR volume>=V_NOTABLE
- SIGNIFICANT: abs_z >= Z_SIGNIFICANT OR abs(return) >= RETURN_SIGNIFICANT OR volume>=V_SIGNIFICANT
- CRITICAL   : abs_z >= Z_CRITICAL OR abs(return) >= RETURN_CRITICAL
- Volume alone may reach SIGNIFICANT but never CRITICAL.
- Corporate events independently contribute a tier (EARNINGS/SIGNIFICANT,
  DIVIDEND/NOTABLE, STOCK_SPLIT/SIGNIFICANT, MERGER_ACQUISITION/CRITICAL,
  TRADING_HALT/CRITICAL, TRADING_RESUMPTION/CRITICAL, MAJOR_ANNOUNCEMENT/SIGNIFICANT).

When z_score is unavailable we evaluate the criteria that ARE available.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.enums import ChangeEventType, CorporateEventType, SignificanceTier
from app.analytics.thresholds import SignificanceThresholds

# Reason codes surfaced to the frontend (stable, user-facing strings).
REASON_PRICE_MOVE = "SIGNIFICANT_PRICE_MOVE"
REASON_UNUSUAL_VOLUME = "UNUSUAL_VOLUME"
REASON_UNUSUAL_RETURN = "UNUSUAL_RETURN"

_CORPORATE_EVENT_TIER: dict[CorporateEventType, SignificanceTier] = {
    CorporateEventType.EARNINGS: SignificanceTier.SIGNIFICANT,
    CorporateEventType.DIVIDEND: SignificanceTier.NOTABLE,
    CorporateEventType.STOCK_SPLIT: SignificanceTier.SIGNIFICANT,
    CorporateEventType.MERGER_ACQUISITION: SignificanceTier.CRITICAL,
    CorporateEventType.TRADING_HALT: SignificanceTier.CRITICAL,
    CorporateEventType.TRADING_RESUMPTION: SignificanceTier.CRITICAL,
    CorporateEventType.MAJOR_ANNOUNCEMENT: SignificanceTier.SIGNIFICANT,
}

# The corporate event types exposed to the feed's ChangeSignal.event_type.
_CORPORATE_SIGNAL_EVENT_TYPE = ChangeEventType.CORPORATE_EVENT

_TIER_ORDER: dict[SignificanceTier, int] = {
    SignificanceTier.CRITICAL: 3,
    SignificanceTier.SIGNIFICANT: 2,
    SignificanceTier.NOTABLE: 1,
    SignificanceTier.NORMAL: 0,
}


@dataclass(frozen=True)
class Classification:
    tier: SignificanceTier
    reason_codes: list[str] = field(default_factory=list)
    event_type: ChangeEventType = ChangeEventType.PRICE_ANOMALY
    event_description: str = ""


def max_tier(a: SignificanceTier, b: SignificanceTier) -> SignificanceTier:
    return a if _TIER_ORDER[a] >= _TIER_ORDER[b] else b


def corporate_event_tier(event_type: CorporateEventType) -> SignificanceTier | None:
    return _CORPORATE_EVENT_TIER.get(event_type)


def classify_price(
    *,
    z: float | None,
    return_pct: float | None,
    thresholds: SignificanceThresholds,
) -> Classification:
    """Classify from price/return/z-score evidence alone."""
    codes: list[str] = []
    tier = SignificanceTier.NORMAL
    abs_ret = abs(return_pct) if return_pct is not None else None
    abs_z = abs(z) if z is not None else None

    if abs_ret is not None and abs_ret >= thresholds.return_critical:
        tier = SignificanceTier.CRITICAL
    elif abs_z is not None and abs_z >= thresholds.z_critical:
        tier = max_tier(tier, SignificanceTier.CRITICAL)

    if abs_ret is not None and abs_ret >= thresholds.return_significant:
        tier = max_tier(tier, SignificanceTier.SIGNIFICANT)
    elif abs_z is not None and abs_z >= thresholds.z_significant:
        tier = max_tier(tier, SignificanceTier.SIGNIFICANT)

    if abs_ret is not None and abs_ret >= thresholds.return_notable:
        tier = max_tier(tier, SignificanceTier.NOTABLE)
    elif abs_z is not None and abs_z >= thresholds.z_notable:
        tier = max_tier(tier, SignificanceTier.NOTABLE)

    if abs_z is not None and abs_z >= thresholds.z_notable:
        codes.append(REASON_UNUSUAL_RETURN)
    elif abs_ret is not None and abs_ret >= thresholds.return_notable:
        codes.append(REASON_PRICE_MOVE)
    if abs_ret is not None and abs_ret >= thresholds.return_notable:
        if REASON_PRICE_MOVE not in codes:
            codes.append(REASON_PRICE_MOVE)

    event_type = ChangeEventType.PRICE_ANOMALY
    if tier is SignificanceTier.NORMAL:
        event_type = ChangeEventType.PRICE_ANOMALY

    return Classification(
        tier=tier,
        reason_codes=codes,
        event_type=event_type,
        event_description="Unusual price movement" if tier is not SignificanceTier.NORMAL else "",
    )


def classify_volume(
    *,
    volume_ratio: float | None,
    thresholds: SignificanceThresholds,
) -> Classification:
    """Classify from volume evidence. Volume can elevate to SIGNIFICANT but not CRITICAL."""
    if volume_ratio is None:
        return Classification(tier=SignificanceTier.NORMAL)
    if volume_ratio >= thresholds.volume_significant:
        return Classification(
            tier=SignificanceTier.SIGNIFICANT,
            reason_codes=[REASON_UNUSUAL_VOLUME],
            event_type=ChangeEventType.VOLUME_ANOMALY,
            event_description="Trading volume increased",
        )
    if volume_ratio >= thresholds.volume_notable:
        return Classification(
            tier=SignificanceTier.NOTABLE,
            reason_codes=[REASON_UNUSUAL_VOLUME],
            event_type=ChangeEventType.VOLUME_ANOMALY,
            event_description="Trading volume increased",
        )
    return Classification(tier=SignificanceTier.NORMAL)


def classify_corporate(event_type: CorporateEventType) -> Classification | None:
    """Classify a corporate event into a change signal."""
    tier = corporate_event_tier(event_type)
    if tier is None:
        return None
    description = _corporate_description(event_type)
    return Classification(
        tier=tier,
        reason_codes=[_corporate_reason(event_type)],
        event_type=_CORPORATE_SIGNAL_EVENT_TYPE,
        event_description=description,
    )


def combine(primary: Classification, others: list[Classification]) -> Classification:
    """Combine signals, keeping objective priority (CRITICAL always wins)."""
    merged = primary
    reason_codes = list(primary.reason_codes)
    tier = primary.tier
    event_type = primary.event_type
    description = primary.event_description
    for other in others:
        if other.tier is SignificanceTier.NORMAL:
            continue
        if _TIER_ORDER[other.tier] > _TIER_ORDER[tier]:
            tier = other.tier
            event_type = other.event_type
            description = other.event_description
        for code in other.reason_codes:
            if code not in reason_codes:
                reason_codes.append(code)
    return Classification(tier=tier, reason_codes=reason_codes, event_type=event_type, event_description=description)


_CORPORATE_REASONS: dict[CorporateEventType, str] = {
    CorporateEventType.EARNINGS: "EARNINGS_EVENT",
    CorporateEventType.DIVIDEND: "DIVIDEND_EVENT",
    CorporateEventType.STOCK_SPLIT: "STOCK_SPLIT_EVENT",
    CorporateEventType.MERGER_ACQUISITION: "MERGER_ACQUISITION_EVENT",
    CorporateEventType.TRADING_HALT: "TRADING_HALT",
    CorporateEventType.TRADING_RESUMPTION: "TRADING_RESUMPTION",
    CorporateEventType.MAJOR_ANNOUNCEMENT: "MAJOR_ANNOUNCEMENT",
}

_CORPORATE_DESCRIPTIONS: dict[CorporateEventType, str] = {
    CorporateEventType.EARNINGS: "Earnings released",
    CorporateEventType.DIVIDEND: "Dividend announced",
    CorporateEventType.STOCK_SPLIT: "Stock split",
    CorporateEventType.MERGER_ACQUISITION: "Merger or acquisition",
    CorporateEventType.TRADING_HALT: "Trading halted",
    CorporateEventType.TRADING_RESUMPTION: "Trading resumed",
    CorporateEventType.MAJOR_ANNOUNCEMENT: "Major announcement",
}


def _corporate_reason(event_type: CorporateEventType) -> str:
    return _CORPORATE_REASONS.get(event_type, "CORPORATE_EVENT")


def _corporate_description(event_type: CorporateEventType) -> str:
    return _CORPORATE_DESCRIPTIONS.get(event_type, event_type.value.replace("_", " ").title())
