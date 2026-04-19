"""Region Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RegionSummary(BaseModel):
    """다른 도메인 응답에 임베드되는 요약 표현."""

    id: int
    name: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class RegionResponse(BaseModel):
    """지역 단건 상세 응답."""

    id: int
    sido: str
    sigungu: str | None
    name: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class RegionSearchQuery(BaseModel):
    q: str = Field(..., min_length=1, max_length=100, description="검색어 (full_name ILIKE)")
    limit: int = Field(20, ge=1, le=100)
