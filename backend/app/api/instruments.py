"""Instrument API routes.

Provides the search endpoint the frontend relies on. Responses match the
frontend's `InstrumentSearchResult` contract: a list of `{ instrument }`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_instrument_service
from app.api.mappers import search_result_out
from app.api.schemas import InstrumentSearchResultOut
from app.application.instrument_service import InstrumentService

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/search", response_model=list[InstrumentSearchResultOut])
def search_instruments(
    service: Annotated[InstrumentService, Depends(get_instrument_service)],
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(20, ge=1, le=50),
) -> list[InstrumentSearchResultOut]:
    return [search_result_out(i) for i in service.search(q, limit=limit)]
