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

logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal"])


@router.post("/cron/ingest")
def cron_ingest(
    x_vercel_cron: Annotated[str | None, Header()] = None,
    x_cron_secret: Annotated[str | None, Header()] = None,
) -> dict:
    settings = get_settings()
    if not settings.CRON_SECRET:
        raise HTTPException(status_code=403, detail="cron ingestion is not configured")
    if x_vercel_cron != "1" and x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")

    quote_result, enrich_result = run_tick(enrich=True)
    logger.info(
        "cron tick ok instruments=%d snapshots=%d invalid=%d failures=%d signals=%d",
        quote_result.instruments,
        quote_result.snapshots,
        quote_result.invalid,
        quote_result.provider_failures,
        enrich_result.signals if enrich_result else 0,
    )
    return {"ok": True}