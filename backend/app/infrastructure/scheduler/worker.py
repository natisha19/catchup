"""Ingestion scheduler.

A simple long-running worker that periodically triggers the IngestionService.
Kept intentionally minimal — it exists to decouple market ingestion from user
requests. The ingestion interval is configurable.

Run as a separate process: `python -m app.infrastructure.scheduler`
"""

from __future__ import annotations

import logging
import time

from app.application.ingestion_service import IngestionService
from app.config import get_settings
from app.infrastructure.database import make_session
from app.infrastructure.repositories.postgres import (
    ChangeSignalRepo,
    CorporateEventRepo,
    InstrumentRepo,
    MarketSnapshotRepo,
)
from app.market_data.yahoo_provider import YahooFinanceProvider

logger = logging.getLogger(__name__)

from app.analytics.thresholds import SignificanceThresholds  # noqa: E402


def build_ingestion_service(session=None) -> IngestionService:
    settings = get_settings()
    if session is None:
        session = make_session()
    return IngestionService(
        provider=YahooFinanceProvider(
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
            max_retries=settings.PROVIDER_MAX_RETRIES,
        ),
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


def run_forever() -> None:
    settings = get_settings()
    interval = settings.INGESTION_INTERVAL_SECONDS
    logger.info("ingestion worker started, interval=%ss", interval)
    while True:
        try:
            result = run_once()
            logger.info(
                "ingestion committed instruments=%d snapshots=%d signals=%d invalid=%d failures=%d",
                result.instruments,
                result.snapshots,
                result.signals,
                result.invalid,
                result.provider_failures,
            )
        except Exception:  # noqa: BLE001 - keep the worker alive across errors
            logger.exception("ingestion run failed")
        time.sleep(interval)


def run_once(instrument_ids: list[str] | None = None):
    """Ad-hoc single ingestion pass (useful for testing/local bootstrap).

    Owns a dedicated session: commits the whole run as one unit on success and
    rolls it back (closing the session) on failure, so partial writes never land.
    """
    session = make_session()
    try:
        service = build_ingestion_service(session)
        result = service.ingest(instrument_ids)
        session.commit()
        logger.info(
            "one-off ingestion committed instruments=%d snapshots=%d signals=%d invalid=%d failures=%d",
            result.instruments,
            result.snapshots,
            result.signals,
            result.invalid,
            result.provider_failures,
        )
        return result
    except Exception:  # noqa: BLE001 - roll back the incomplete unit
        session.rollback()
        logger.exception("ingestion run failed; rolled back and closed session")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_forever()
