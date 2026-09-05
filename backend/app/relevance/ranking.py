"""V1 rule-based relevance ranker.

Rules:
- CRITICAL always first (visibility is guaranteed).
- SIGNIFICANT always after CRITICAL.
- Within the same tier, a simple deterministic score pushes events the user has
  historically engaged with slightly higher. V1 keeps it neutral/cold-start:
  there is no tracking of clicks-as-strong-preference, so with no data all
  events within a tier keep their chronological order.

This is deliberately simple but behind the RelevanceRanker interface so a more
sophisticated algorithm can be swapped in without touching the API/domain.
"""

from __future__ import annotations

from app.domain.entities import ChangeSignal
from app.domain.enums import SignificanceTier

_TIER_ORDER = {
    SignificanceTier.CRITICAL: 3,
    SignificanceTier.SIGNIFICANT: 2,
    SignificanceTier.NOTABLE: 1,
    SignificanceTier.NORMAL: 0,
}


class RuleBasedRelevanceRanker:
    def rank(self, changes: list[ChangeSignal], user_id: str) -> list[ChangeSignal]:
        # Objective tier order is the primary, non-negotiable ordering.
        # Within a tier, keep stable incoming order (no personalization data yet).
        return sorted(
            changes,
            key=lambda c: (_TIER_ORDER[c.significance], c.observed_at or ""),
            reverse=True,
        )
