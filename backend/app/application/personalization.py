"""Watchlist-composition personalization.

Requirement (spec §12): personalization must be derived from REAL user
behavior — the sectors actually present in the user's watchlist — never from a
fabricated "you care about X" claim and never for the cold-start user.

Rules:
  * Cold-start suppression: with fewer than MIN_ITEMS instruments (no basis) the
    observation is None and the UI shows nothing.
  * The summary is a factual statement about the watchlist's sector composition.
  * Ranking is untouched here: CRITICAL visibility is governed solely by the
    objective relevance ranker, never by this summary.
"""

from __future__ import annotations

from collections import Counter

from app.domain.entities import Instrument, UserRelevance

# No reliable observation below this many instruments (spec: cold-start
# suppression — don't guess from a single holding).
MIN_ITEMS = 3


def watchlist_composition(instruments: list[Instrument]) -> UserRelevance | None:
    """A factual, sector-composition summary, or None when there is no basis."""
    if len(instruments) < MIN_ITEMS:
        return None
    counts = Counter(inst.sector for inst in instruments if inst.sector)
    if not counts:
        return None
    sector, count = counts.most_common(1)[0]
    summary = (
        f"{sector} is the most common sector in your watchlist"
        f" ({count} of {len(instruments)} stocks)."
    )
    return UserRelevance(summary=summary)