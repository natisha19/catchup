"""Catchup API routes.

Thin handlers: validate input, call services, map to schemas. No z-score math,
no database queries, no provider calls here.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_catchup_service,
    get_instrument_service,
    get_user_id,
)
from app.api.mappers import detail_out, feed_out, instrument_lookup
from app.api.schemas import CatchupFeedOut, ChangeDetailOut, MarkSeenRequest
from app.application.catchup_service import CatchupService, InstrumentNotFoundError
from app.application.instrument_service import InstrumentService

router = APIRouter(prefix="/catchup", tags=["catchup"])


@router.get("", response_model=CatchupFeedOut)
def get_feed(
    user_id: Annotated[str, Depends(get_user_id)],
    catchup: Annotated[CatchupService, Depends(get_catchup_service)],
) -> CatchupFeedOut:
    lookup = instrument_lookup(catchup.watchlist_instruments(user_id))
    feed = catchup.get_feed(user_id)
    return feed_out(feed, lookup)


@router.get("/{instrument_id}", response_model=ChangeDetailOut)
def get_instrument_change(
    instrument_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
    catchup: Annotated[CatchupService, Depends(get_catchup_service)],
    instruments: Annotated[InstrumentService, Depends(get_instrument_service)],
) -> ChangeDetailOut:
    try:
        detail = catchup.get_instrument_change(user_id, instrument_id)
    except InstrumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    inst = instruments.get(instrument_id)
    lookup = instrument_lookup([inst] if inst else [])
    return detail_out(detail, lookup)


@router.post("/mark-seen", status_code=status.HTTP_200_OK)
def mark_seen(
    user_id: Annotated[str, Depends(get_user_id)],
    catchup: Annotated[CatchupService, Depends(get_catchup_service)],
    body: MarkSeenRequest | None = None,
) -> None:
    catchup.mark_seen(
        user_id,
        body.instrument_id if body else None,
        body.snapshot_ids if body else None,
    )
