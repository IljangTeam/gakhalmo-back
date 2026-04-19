"""Region API router."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import AsyncSessionDep
from app.domain.regions.schemas import RegionResponse, RegionSummary
from app.domain.regions.service import RegionService

router = APIRouter(prefix="/regions", tags=["Regions"])


@router.get(
    "/search",
    response_model=list[RegionSummary],
    summary="지역 검색 (자동완성)",
)
async def search_regions(
    session: AsyncSessionDep,
    q: str = Query(..., min_length=1, max_length=100, description="검색어 (full_name ILIKE)"),
    limit: int = Query(20, ge=1, le=100),
) -> list[RegionSummary]:
    service = RegionService(session)
    regions = await service.search(q, limit=limit)
    return [RegionSummary.model_validate(r) for r in regions]


@router.get(
    "/{region_id}",
    response_model=RegionResponse,
    summary="지역 단건 조회",
)
async def get_region(
    region_id: int,
    session: AsyncSessionDep,
) -> RegionResponse:
    service = RegionService(session)
    region = await service.get_by_id(region_id)
    return RegionResponse.model_validate(region)
