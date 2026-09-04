"""Catchup backend entrypoint.

Wires routers, CORS, structured logging, and health. Depends on nothing but
FastAPI at this layer; domain/application/infrastructure are composed in
app.api.deps.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import auth, catchup, instruments, watchlists
from app.config import get_settings
from app.infrastructure.database import get_session

logging.basicConfig(
    level=get_settings().LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Structured logging + optional ingestion startup would hook here. Ingestion
    # runs as a separate worker process (see infrastructure.scheduler) so the
    # API stays decoupled from provider availability.
    logger.info("Catchup API starting")
    yield
    logger.info("Catchup API stopped")


app = FastAPI(
    title="Catchup API",
    version="0.1.0",
    description=(
        "Remembers the market state when a user last checked and reports what "
        "meaningfully changed when they return."
    ),
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catchup.router)
app.include_router(watchlists.router)
app.include_router(instruments.router)


@app.get("/health", tags=["health"])
def health(session: Annotated[Session, Depends(get_session)]) -> dict:
    """Verify basic application + database availability."""
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - surface connectivity as a stable shape
        logger.exception("health check database failure")
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}
