"""Domain -> API schema mappers.

Thin converters that turn domain dataclasses into the public wire contract.
Enrichments that the frontend needs but the domain does not store (symbol /
company name on a ChangeSignal) happen here.
"""

from __future__ import annotations

from app.api.schemas import (
    CatchupFeedOut,
    ChangeDetailOut,
    ChangeSignalOut,
    ExploreItemOut,
    ExploreOut,
    InstrumentOut,
    InstrumentSearchResultOut,
    MarketSnapshotOut,
    UserRelevanceOut,
    WatchlistItemOut,
    WatchlistOut,
)
from app.domain.entities import (
    CatchupFeed,
    ChangeDetail,
    ChangeSignal,
    ExploreItem,
    ExploreSections,
    Instrument,
    MarketSnapshot,
    UserRelevance,
    Watchlist,
    WatchlistItem,
)
from app.domain.enums import BaselineStatus, SignificanceTier


def instrument_out(inst: Instrument) -> InstrumentOut:
    return InstrumentOut(
        instrument_id=inst.instrument_id,
        symbol=inst.symbol,
        company_name=inst.company_name,
        exchange=inst.exchange,
        currency=inst.currency,
        sector=inst.sector,
    )


def snapshot_out(snap: MarketSnapshot) -> MarketSnapshotOut:
    return MarketSnapshotOut(
        instrument_id=snap.instrument_id,
        observed_at=snap.observed_at,
        received_at=snap.received_at,
        price=snap.price,
        open=snap.open,
        high=snap.high,
        low=snap.low,
        close=snap.close,
        volume=snap.volume,
        source=snap.source,
        data_status=snap.data_status.value,
    )


def signal_out(signal: ChangeSignal, lookup: dict[str, Instrument]) -> ChangeSignalOut:
    inst = lookup.get(signal.instrument_id)
    symbol = inst.symbol if inst else signal.instrument_id
    company = inst.company_name if inst else ""
    return ChangeSignalOut(
        id=str(signal.id or ""),
        instrument_id=signal.instrument_id,
        symbol=symbol,
        company_name=company,
        previous_price=signal.previous_price,
        current_price=signal.current_price,
        return_pct=signal.return_pct,
        baseline_mean=signal.baseline_mean,
        baseline_std=signal.baseline_std,
        z_score=signal.z_score,
        current_volume=signal.current_volume,
        baseline_average_volume=signal.baseline_average_volume,
        volume_ratio=signal.volume_ratio,
        event_type=signal.event_type.value,
        reason_codes=signal.reason_codes,
        event_description=signal.event_description,
        significance=signal.significance.value,
        observed_at=signal.observed_at,
        data_status=signal.data_status.value,
    )


def relevance_out(r: UserRelevance) -> UserRelevanceOut:
    return UserRelevanceOut(summary=r.summary, top_reason_codes=r.top_reason_codes)


def feed_out(feed: CatchupFeed, lookup: dict[str, Instrument]) -> CatchupFeedOut:
    return CatchupFeedOut(
        last_checked_at=feed.last_checked_at,
        market_status=feed.market_status.value,
        last_market_session_at=feed.last_market_session_at,
        changes=[signal_out(c, lookup) for c in feed.changes],
        unchanged_count=feed.unchanged_count,
        provider_status=feed.provider_status.value if feed.provider_status else None,
        user_relevance=relevance_out(feed.user_relevance) if feed.user_relevance else None,
        acknowledgement=feed.acknowledgement,
    )


def detail_out(detail: ChangeDetail, lookup: dict[str, Instrument]) -> ChangeDetailOut:
    return ChangeDetailOut(
        instrument=instrument_out(detail.instrument),
        snapshot=snapshot_out(detail.snapshot) if detail.snapshot else None,
        previous_seen_price=detail.previous_seen_price,
        latest_signal=(
            signal_out(detail.latest_signal, lookup) if detail.latest_signal else None
        ),
        other_signals=[signal_out(s, lookup) for s in detail.other_signals],
        last_checked_note=detail.last_checked_note,
        market_status=detail.market_status.value if detail.market_status else None,
    )


def watchlist_item_out(item: WatchlistItem) -> WatchlistItemOut:
    # Frontend contract only knows READY | INSUFFICIENT.
    baseline: str
    if item.baseline_status in (
        BaselineStatus.SUFFICIENT,
        BaselineStatus.LIMITED,
    ):
        baseline = "READY"
    else:
        baseline = "INSUFFICIENT"
    return WatchlistItemOut(
        instrument=instrument_out(item.instrument),
        added_at=item.added_at,
        baseline_status=baseline,
    )


def watchlist_out(watchlist: Watchlist) -> WatchlistOut:
    return WatchlistOut(
        items=[watchlist_item_out(i) for i in watchlist.items],
        updated_at=watchlist.updated_at,
    )


def search_result_out(inst: Instrument) -> InstrumentSearchResultOut:
    return InstrumentSearchResultOut(instrument=instrument_out(inst))


def explore_item_out(item: ExploreItem, lookup: dict[str, Instrument]) -> ExploreItemOut:
    return ExploreItemOut(
        instrument=instrument_out(item.instrument),
        snapshot=snapshot_out(item.snapshot) if item.snapshot else None,
        signal=signal_out(item.signal, lookup) if item.signal else None,
    )


def explore_out(sections: ExploreSections, lookup: dict[str, Instrument]) -> ExploreOut:
    return ExploreOut(
        movers=[explore_item_out(i, lookup) for i in sections.movers],
        dippers=[explore_item_out(i, lookup) for i in sections.dippers],
        unusual=[explore_item_out(i, lookup) for i in sections.unusual],
        sectors=sections.sectors,
    )


def instrument_lookup(instruments: list[Instrument]) -> dict[str, Instrument]:
    return {i.instrument_id: i for i in instruments}
