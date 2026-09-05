"""Instrument API routes.

Provides the search endpoint the frontend relies on. Responses match the
frontend's `InstrumentSearchResult` contract: a list of `{ instrument }`.
Also serves the Explore feed (movers / dippers / unusual / sectors), which is
read-side only and computed from real persisted snapshots + signals.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_explore_service, get_instrument_service
from app.api.mappers import explore_out, search_result_out
from app.api.schemas import ExploreOut, InstrumentSearchResultOut
from app.application.explore_service import ExploreService
from app.application.instrument_service import InstrumentService

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/search", response_model=list[InstrumentSearchResultOut])
def search_instruments(
    service: Annotated[InstrumentService, Depends(get_instrument_service)],
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(20, ge=1, le=50),
) -> list[InstrumentSearchResultOut]:
    return [search_result_out(i) for i in service.search(q, limit=limit)]


@router.get("/explore", response_model=ExploreOut)
def explore(
    service: Annotated[ExploreService, Depends(get_explore_service)],
    limit: int = Query(6, ge=1, le=50),
    sector: str | None = Query(None, max_length=64),
) -> ExploreOut:
    sections = service.sections(limit=limit, sector=sector)
    lookup = {i.instrument.instrument_id: i.instrument for i in [
        *sections.movers, *sections.dippers, *sections.unusual,
    ]}
    return explore_out(sections, lookup)
