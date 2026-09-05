"""Relevance package.

Objective significance (how unusual is the event) is SEPARATE from user
relevance (how relevant to this particular user). Relevance may re-rank within
a tier but must never suppress CRITICAL or SIGNIFICANT events.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.entities import ChangeSignal


class RelevanceRanker(Protocol):
    """Replaceable interface for ranking/personalization."""

    def rank(self, changes: list[ChangeSignal], user_id: str) -> list[ChangeSignal]: ...
