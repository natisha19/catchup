"""FastAPI dependency wiring.

Composes repository implementations with application services from a request
scope. This is the composition root for the API so routes stay thin and never
build services themselves.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.analytics.thresholds import SignificanceThresholds
from app.application.catchup_service import CatchupService
from app.application.ingestion_service import IngestionService
from app.application.instrument_service import InstrumentService
from app.application.watchlist_service import WatchlistService
from app.config import get_settings
from app.infrastructure.database import get_session
from app.infrastructure.repositories.postgres import (
    ChangeSignalRepo,
    CorporateEventRepo,
    InstrumentRepo,
    MarketSnapshotRepo,
    UserLastSeenRepo,
    WatchlistRepo,
)
from app.relevance.ranking import RuleBasedRelevanceRanker

# A single-user product today. This is the seam where real authentication can be
# introduced without touching the domain or services.
DEFAULT_USER_ID = "default-user"


def _provider():
    from app.market_data.yahoo_provider import YahooFinanceProvider

    settings = get_settings()
    return YahooFinanceProvider(
        timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        max_retries=settings.PROVIDER_MAX_RETRIES,
    )


def get_user_id() -> str:
    return DEFAULT_USER_ID


def get_instrument_service(
    session: Annotated[Session, Depends(get_session)],
) -> InstrumentService:
    return InstrumentService(InstrumentRepo(session))


def get_watchlist_service(
    session: Annotated[Session, Depends(get_session)],
) -> WatchlistService:
    settings = get_settings()
    instrument_service = InstrumentService(
        InstrumentRepo(session), provider=_provider()
    )
    return WatchlistService(
        watchlists=WatchlistRepo(session),
        instruments=InstrumentRepo(session),
        snapshots=MarketSnapshotRepo(session),
        min_baseline_returns=settings.MIN_BASELINE_RETURNS,
        resolver=instrument_service.resolve_and_save,
    )


def get_catchup_service(
    session: Annotated[Session, Depends(get_session)],
) -> CatchupService:
    settings = get_settings()
    return CatchupService(
        watchlists=WatchlistRepo(session),
        instruments=InstrumentRepo(session),
        snapshots=MarketSnapshotRepo(session),
        signals=ChangeSignalRepo(session),
        last_seen=UserLastSeenRepo(session),
        ranker=RuleBasedRelevanceRanker(),
        min_baseline_returns=settings.MIN_BASELINE_RETURNS,
        stale_threshold_minutes=settings.STALE_THRESHOLD_MINUTES,
    )


def get_thresholds() -> SignificanceThresholds:
    return SignificanceThresholds.from_settings(get_settings())


def get_ingestion_service(
    session: Annotated[Session, Depends(get_session)],
) -> IngestionService:
    settings = get_settings()
    return IngestionService(
        provider=_provider(),
        instruments=InstrumentRepo(session),
        snapshots=MarketSnapshotRepo(session),
        events=CorporateEventRepo(session),
        signals=ChangeSignalRepo(session),
        thresholds=SignificanceThresholds.from_settings(settings),
        baseline_window_days=settings.BASELINE_WINDOW_DAYS,
        min_baseline_returns=settings.MIN_BASELINE_RETURNS,
        limited_baseline_returns=settings.LIMITED_BASELINE_RETURNS,
        delayed_threshold_minutes=settings.DELAYED_THRESHOLD_MINUTES,
        stale_threshold_minutes=settings.STALE_THRESHOLD_MINUTES,
    )
