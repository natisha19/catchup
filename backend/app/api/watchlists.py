"""Watchlist API routes.

Thin handlers delegating to WatchlistService. Provides both the full REST
surface (per spec §41) and `/watchlists/me` used by the existing frontend's
single implicit watchlist.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_catchup_service, get_user_id, get_watchlist_service
from app.api.mappers import detail_out, instrument_lookup, watchlist_out
from app.api.schemas import (
    AddItemRequest,
    ChangeDetailOut,
    CreateWatchlistRequest,
    WatchlistOut,
    WatchlistSummaryOut,
)
from app.application.catchup_service import CatchupService
from app.application.instrument_service import InstrumentNotFoundError
from app.application.watchlist_service import (
    DuplicateWatchlistItemError,
    WatchlistNotFoundError,
    WatchlistService,
)

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("", response_model=list[WatchlistSummaryOut])
def list_watchlists(
    user_id: Annotated[str, Depends(get_user_id)],
    service: Annotated[WatchlistService, Depends(get_watchlist_service)],
) -> list[WatchlistSummaryOut]:
    return [WatchlistSummaryOut(**w) for w in service.list_watchlists(user_id)]


@router.post("", response_model=WatchlistSummaryOut, status_code=status.HTTP_201_CREATED)
def create_watchlist(
    user_id: Annotated[str, Depends(get_user_id)],
    service: Annotated[WatchlistService, Depends(get_watchlist_service)],
    body: CreateWatchlistRequest | None = None,
) -> WatchlistSummaryOut:
    summary = service.create_watchlist(user_id, body.name if body else "My watchlist")
    return WatchlistSummaryOut(**summary)


@router.get("/me", response_model=WatchlistOut)
def get_my_watchlist(
    user_id: Annotated[str, Depends(get_user_id)],
    service: Annotated[WatchlistService, Depends(get_watchlist_service)],
) -> WatchlistOut:
    return watchlist_out(service.get(user_id))


@router.get("/me/snapshots", response_model=list[ChangeDetailOut])
def get_my_watchlist_snapshots(
    user_id: Annotated[str, Depends(get_user_id)],
    catchup: Annotated[CatchupService, Depends(get_catchup_service)],
) -> list[ChangeDetailOut]:
    """One dashboard request for all currently watched market snapshots."""
    instruments = catchup.watchlist_instruments(user_id)
    lookup = instrument_lookup(instruments)
    return [
        detail_out(detail, lookup)
        for detail in catchup.get_watchlist_snapshot_details(user_id)
    ]


@router.post("/me/items", status_code=status.HTTP_201_CREATED)
def add_my_watchlist_item(
    body: AddItemRequest,
    user_id: Annotated[str, Depends(get_user_id)],
    service: Annotated[WatchlistService, Depends(get_watchlist_service)],
) -> None:
    try:
        service.add_item(user_id, body.instrument_id, body.symbol)
    except DuplicateWatchlistItemError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InstrumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/me/items/{instrument_id}", status_code=status.HTTP_200_OK)
def remove_my_watchlist_item(
    instrument_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
    service: Annotated[WatchlistService, Depends(get_watchlist_service)],
) -> None:
    try:
        service.remove_item(user_id, instrument_id)
    except WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{watchlist_id}/items", response_model=WatchlistOut)
def get_watchlist_items(
    watchlist_id: int,
    user_id: Annotated[str, Depends(get_user_id)],
    service: Annotated[WatchlistService, Depends(get_watchlist_service)],
) -> WatchlistOut:
    try:
        return watchlist_out(service.get_for_watchlist(user_id, watchlist_id))
    except WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{watchlist_id}/items", status_code=status.HTTP_201_CREATED)
def add_watchlist_item(
    watchlist_id: int,
    body: AddItemRequest,
    user_id: Annotated[str, Depends(get_user_id)],
    service: Annotated[WatchlistService, Depends(get_watchlist_service)],
) -> None:
    try:
        service.add_item_to_watchlist(user_id, watchlist_id, body.instrument_id, body.symbol)
    except WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateWatchlistItemError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InstrumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{watchlist_id}/items/{instrument_id}", status_code=status.HTTP_200_OK)
def remove_watchlist_item(
    watchlist_id: int,
    instrument_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
    service: Annotated[WatchlistService, Depends(get_watchlist_service)],
) -> None:
    try:
        service.remove_item_from_watchlist(user_id, watchlist_id, instrument_id)
    except WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
