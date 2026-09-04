"""Catchup service — the core operation.

Answers "what meaningfully changed in this user's watchlist since they last
checked?" by combining:

- MARKET STATE: latest validated snapshot + latest change signal (shared,
  computed at ingestion time).
- USER STATE: per (user_id, instrument_id) last-seen snapshot.

Depends only on repository interfaces and the relevance ranker — never on a
database session or a market provider directly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.application.market_clock import market_status
from app.domain.entities import (
    CatchupFeed,
    ChangeDetail,
    ChangeSignal,
    MarketSnapshot,
    UserLastSeen,
    UserRelevance,
    Watchlist,
)
from app.domain.enums import MarketStatus, ProviderStatus, SignificanceTier
from app.domain.interfaces.repositories import (
    ChangeSignalRepository,
    InstrumentRepository,
    MarketSnapshotRepository,
    UserLastSeenRepository,
    WatchlistRepository,
)

logger = logging.getLogger(__name__)


class InstrumentNotFoundError(Exception):
    pass


class CatchupService:
    def __init__(
        self,
        watchlists: WatchlistRepository,
        instruments: InstrumentRepository,
        snapshots: MarketSnapshotRepository,
        signals: ChangeSignalRepository,
        last_seen: UserLastSeenRepository,
        ranker,
        min_baseline_returns: int,
        stale_threshold_minutes: int,
    ) -> None:
        self._watchlists = watchlists
        self._instruments = instruments
        self._snapshots = snapshots
        self._signals = signals
        self._last_seen = last_seen
        self._ranker = ranker
        self._min_baseline_returns = min_baseline_returns
        self._stale_threshold_minutes = stale_threshold_minutes

    # ------------------------------------------------------------------ feed
    def watchlist_instruments(self, user_id: str) -> list:
        watchlist = self._watchlists.get_items(user_id)
        return [it.instrument for it in watchlist.items]

    def get_feed(self, user_id: str) -> CatchupFeed:
        watchlist = self._watchlists.get_items(user_id)
        instrument_ids = [it.instrument.instrument_id for it in watchlist.items]

        seen_map = self._last_seen.get_all(user_id)
        latest_snapshots = {
            iid: self._snapshots.get_latest(iid) for iid in instrument_ids
        }

        # Fetch every signal in the catch-up window (not just the latest per
        # instrument) so a later NORMAL signal can never erase an earlier, more
        # significant event. Each instrument is then consolidated to one
        # headline entry.
        clip = self._window_clip(seen_map, instrument_ids)
        signals_by_instrument = self._signals.history(instrument_ids, since=clip)

        changes: list[ChangeSignal] = []
        unchanged = 0

        for it in watchlist.items:
            iid = it.instrument.instrument_id
            snapshot = latest_snapshots.get(iid)
            if snapshot is None:
                # No observed data yet — baseline establishing or provider has
                # no data. Never fabricate a change.
                unchanged += 1
                continue

            seen = seen_map.get(iid)
            meaningful = [
                s
                for s in signals_by_instrument.get(iid, [])
                if self._is_new_since_last_seen(s, seen)
                and s.significance is not SignificanceTier.NORMAL
            ]
            if not meaningful:
                unchanged += 1
                continue
            changes.append(self._consolidate(meaningful))

        ordered = self._ranker.rank(changes, user_id)

        latest_observed = self._latest_observed_at(latest_snapshots, instrument_ids)
        market = market_status(
            latest_observed,
            stale_threshold_minutes=self._stale_threshold_minutes,
        )
        provider = self._provider_status(latest_snapshots.values())
        last_checked = self._global_last_checked(seen_map)

        return CatchupFeed(
            last_checked_at=last_checked,
            market_status=market,
            last_market_session_at=latest_observed,
            changes=ordered,
            unchanged_count=unchanged,
            provider_status=provider,
            user_relevance=self._ranker.relevance_summary(ordered, user_id),
            acknowledgement={
                iid: snapshot.id if snapshot else None
                for iid, snapshot in latest_snapshots.items()
            },
        )

    # ------------------------------------------------------- instrument detail
    def get_instrument_change(self, user_id: str, instrument_id: str) -> ChangeDetail:
        instrument = self._instruments.get(instrument_id)
        if instrument is None:
            raise InstrumentNotFoundError(instrument_id)

        snapshot = self._snapshots.get_latest(instrument_id)
        seen = self._last_seen.get(user_id, instrument_id)

        # Full auditable list of meaningful events since the user last checked,
        # not just the single most recent signal.
        clip = self._window_clip(
            {instrument_id: seen} if seen else {}, [instrument_id]
        )
        all_signals = self._signals.history(
            [instrument_id], since=clip
        ).get(instrument_id, [])
        meaningful = [
            s
            for s in all_signals
            if self._is_new_since_last_seen(s, seen)
            and s.significance is not SignificanceTier.NORMAL
        ]

        if meaningful:
            headline = self._consolidate(meaningful)
            other_signals = [s for s in meaningful if s.id != headline.id]
        else:
            headline = None
            other_signals = []

        previous_seen_price = None
        if seen and seen.last_seen_snapshot_id is not None:
            seen_snap = self._snapshots.get_by_id(seen.last_seen_snapshot_id)
            previous_seen_price = seen_snap.price if seen_snap else None

        return ChangeDetail(
            instrument=instrument,
            snapshot=snapshot,
            previous_seen_price=previous_seen_price,
            latest_signal=headline,
            other_signals=other_signals,
            last_checked_note=(
                seen.last_seen_at.isoformat() if seen else None
            ),
        )

    # ------------------------------------------------------------- mark seen
    def mark_seen(
        self,
        user_id: str,
        instrument_id: str | None = None,
        snapshot_ids: dict[str, int | None] | None = None,
    ) -> None:
        """Record that the user checked this instrument (or all of them).

        A generated signal does NOT mean the user saw it. Only this explicit
        call advances last_seen.
        """
        watchlist = self._watchlists.get_items(user_id)
        ids = (
            [instrument_id]
            if instrument_id
            else [it.instrument.instrument_id for it in watchlist.items]
        )
        now = datetime.now(timezone.utc)

        for iid in ids:
            # Acknowledge exactly the watermark sent in the feed. Falling back
            # to latest preserves backwards compatibility for a single detail
            # acknowledgement, but feed clients always send snapshot_ids.
            if snapshot_ids is not None:
                # Missing/None means this feed did not deliver a snapshot for
                # the instrument. Never substitute a newer one in that case.
                if iid not in snapshot_ids:
                    continue
                snapshot_id = snapshot_ids[iid]
                latest = (
                    self._snapshots.get_by_id(snapshot_id)
                    if snapshot_id is not None
                    else None
                )
            else:
                latest = self._snapshots.get_latest(iid)
            if latest is not None and latest.instrument_id != iid:
                logger.warning("ignoring invalid acknowledgement user=%s instrument=%s snapshot=%s", user_id, iid, snapshot_id)
                continue
            self._last_seen.upsert(
                UserLastSeen(
                    user_id=user_id,
                    instrument_id=iid,
                    last_seen_at=now,
                    last_seen_snapshot_id=latest.id if latest else None,
                )
            )

    # ------------------------------------------------------------ helpers ----
    @staticmethod
    def _is_new_since_last_seen(signal: ChangeSignal, seen: UserLastSeen | None) -> bool:
        if seen is None:
            return True  # first time this user sees the instrument
        if seen.last_seen_snapshot_id is None:
            return True
        if signal.current_snapshot_id is not None:
            return signal.current_snapshot_id > seen.last_seen_snapshot_id
        return signal.observed_at > seen.last_seen_at

    @staticmethod
    def _window_clip(
        seen_map: dict[str, UserLastSeen], instrument_ids: list[str]
    ) -> datetime | None:
        """Recency bound for the signal fetch.

        Returns the earliest last-seen among the instruments, so no meaningful
        event after any user's check is ever missed. Returns None when nothing
        has been seen yet, meaning "fetch from the start" — the repository caps
        per-instrument count to keep the query bounded.
        """
        cutoff: datetime | None = None
        for iid in instrument_ids:
            seen = seen_map.get(iid)
            if seen and seen.last_seen_at:
                if cutoff is None or seen.last_seen_at < cutoff:
                    cutoff = seen.last_seen_at
        return cutoff

    @staticmethod
    def _consolidate(signals: list[ChangeSignal]) -> ChangeSignal:
        """Pick the headline from a set of meaningful signals.

        Preserves the strongest evidence: highest significance tier, then the
        largest absolute move (return %), then the most recent. A later NORMAL
        signal is excluded upstream, so it can never erase this headline.
        """
        tier_rank = {
            SignificanceTier.CRITICAL: 0,
            SignificanceTier.SIGNIFICANT: 1,
            SignificanceTier.NOTABLE: 2,
        }

        def key(s: ChangeSignal):
            return (
                -tier_rank[s.significance],
                abs(s.return_pct) if s.return_pct is not None else -1.0,
                s.observed_at,
            )

        return max(signals, key=key)

    @staticmethod
    def _global_last_checked(seen_map: dict[str, UserLastSeen]) -> datetime | None:
        if not seen_map:
            return None
        return max(s.last_seen_at for s in seen_map.values())

    @staticmethod
    def _latest_observed_at(
        latest_snapshots: dict[str, MarketSnapshot | None],
        instrument_ids: list[str],
    ) -> datetime | None:
        times = [
            latest_snapshots[iid].observed_at
            for iid in instrument_ids
            if latest_snapshots.get(iid) and latest_snapshots[iid].observed_at
        ]
        return max(times) if times else None

    @staticmethod
    def _provider_status(snapshots) -> ProviderStatus:
        present = [s for s in snapshots if s is not None]
        if not present:
            return ProviderStatus.UNAVAILABLE
        statuses = {s.data_status for s in present}
        if "UNAVAILABLE" in statuses and statuses == {"UNAVAILABLE"}:
            return ProviderStatus.UNAVAILABLE
        if "LIVE" in statuses:
            return ProviderStatus.AVAILABLE
        return ProviderStatus.DEGRADED
