"""Ingestion scheduler.

A simple long-running worker that periodically triggers the IngestionService.
Kept intentionally minimal — it exists to decouple market ingestion from user
requests. The ingestion interval is configurable.

Two cadences drive the system:
  * every ``INGESTION_INTERVAL_SECONDS``  -> fast quote phase (fresh snapshots)
  * every ``INGESTION_ENRICHMENT_INTERVAL_SECONDS`` -> slow enrichment phase
    (baseline history + corporate events -> signals). This is the provider
    rate-limit: history is only re-fetched on this cadence, not every tick.

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
from app.market_data.catalog import default_catalog
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
        quote_workers=settings.INGESTION_QUOTE_WORKERS,
        catalog=default_catalog(),
    )


def run_tick(
    enrich: bool,
    instrument_ids: list[str] | None = None,
) -> tuple:
    """One worker tick: quotes always, enrichment only when due.

    Owns a dedicated session and commits the whole tick as one unit on success,
    rolling back (and closing the session) on failure so partial writes never land.
    """
    session = make_session()
    try:
        service = build_ingestion_service(session)
        quote_result = service.quote(instrument_ids)
        enrich_result = None
        if enrich:
            enrich_result = service.enrich(instrument_ids)
        session.commit()
        logger.info(
            "ingestion tick committed quotes(instruments=%d snapshots=%d invalid=%d failures=%d) enrich=%s",
            quote_result.instruments,
            quote_result.snapshots,
            quote_result.invalid,
            quote_result.provider_failures,
            "yes" if enrich else "no",
        )
        if enrich_result is not None:
            logger.info(
                "enrichment committed signals=%d",
                enrich_result.signals,
            )
        return quote_result, enrich_result
    except Exception:  # noqa: BLE001 - roll back the incomplete unit
        session.rollback()
        logger.exception("ingestion tick failed; rolled back and closed session")
        raise
    finally:
        session.close()


def run_forever() -> None:
    settings = get_settings()
    quote_interval = settings.INGESTION_INTERVAL_SECONDS
    enrich_interval = settings.INGESTION_ENRICHMENT_INTERVAL_SECONDS
    next_enrich_at = time.monotonic()
    logger.info(
        "ingestion worker started, quote_interval=%ss enrich_interval=%ss already_due=%s",
        quote_interval,
        enrich_interval,
        next_enrich_at <= time.monotonic(),
    )
    while True:
        now = time.monotonic()
        try:
            run_tick(enrich=now >= next_enrich_at)
            if now >= next_enrich_at:
                next_enrich_at = now + enrich_interval
        except Exception:  # noqa: BLE001 - keep the worker alive across errors
            logger.exception("ingestion tick failed")
        time.sleep(quote_interval)


def run_once(instrument_ids: list[str] | None = None):
    """Ad-hoc single full pass (quotes + enrichment), useful for local bootstrap.

    ``run_once`` deliberately runs both phases so a one-off call seeds snapshots
    AND baselines/signals. ``run_forever`` is the split-cadence loop.
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