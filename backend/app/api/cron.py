"""Serverless ingestion trigger (Vercel Cron).

Vercel has no long-running processes, so the always-on worker
(``run_forever``) cannot run there. This endpoint lets a Vercel Cron invoke one
self-contained tick — quotes + enrichment, own DB session, committed as one unit
— the serverless equivalent of the worker's loop body.

Guarded two ways: Vercel marks its cron requests with the ``x-vercel-cron``
header, and any other caller must present ``x-cron-secret`` matching
``CRON_SECRET``. If ``CRON_SECRET`` is empty the endpoint refuses to run.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.infrastructure.scheduler.worker import run_tick
import yfinance as yf

logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal"])


@router.api_route("/cron/ingest", methods=["GET", "POST"])
def cron_ingest(
    x_vercel_cron: Annotated[str | None, Header()] = None,
    x_cron_secret: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    settings = get_settings()

    if not settings.CRON_SECRET:
        raise HTTPException(
            status_code=403,
            detail="cron ingestion is not configured",
        )

    valid_header_secret = x_cron_secret == settings.CRON_SECRET
    valid_bearer_secret = authorization == f"Bearer {settings.CRON_SECRET}"
    valid_vercel_cron = x_vercel_cron == "1"

    if not (valid_header_secret or valid_bearer_secret or valid_vercel_cron):
        raise HTTPException(status_code=403, detail="forbidden")

    try:
        quote_result, enrich_result = run_tick(enrich=True)
    except Exception as exc:
        logger.exception("cron ingestion failed")
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc

    logger.info(
        "cron tick ok instruments=%d snapshots=%d invalid=%d failures=%d signals=%d",
        quote_result.instruments,
        quote_result.snapshots,
        quote_result.invalid,
        quote_result.provider_failures,
        enrich_result.signals if enrich_result else 0,
    )

    return {"ok": True}


@router.get("/cron/yahoo-test")
def yahoo_test() -> dict:
    results = {}

    for symbol in ["TCS.NS", "SBIN.NS"]:
        try:
            bars = yf.Ticker(symbol).history(
                period="1d",
                interval="1m",
                auto_adjust=False,
            )

            if bars is None or bars.empty:
                results[symbol] = {
                    "ok": False,
                    "error": "empty response",
                }
                continue

            when, bar = next(reversed(list(bars.iterrows())))

            results[symbol] = {
                "ok": True,
                "last_timestamp": str(when),
                "last_close": float(bar["Close"]),
                "rows": len(bars),
            }

        except Exception as exc:
            results[symbol] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    return results