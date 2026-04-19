"""Region 도메인 서비스."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.regions.models import Region
from app.domain.regions.repository import RegionRepository


class RegionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = RegionRepository(session)

    async def get_by_id(self, region_id: int) -> Region:
        region = await self.repository.get_by_id(region_id)
        if region is None:
            raise NotFoundError(detail="지역을 찾을 수 없습니다.")
        return region

    async def ensure_exists(self, region_id: int) -> None:
        """FK 유효성 검증 — 존재하지 않으면 NotFoundError."""
        await self.get_by_id(region_id)

    async def search(self, query: str, *, limit: int = 20) -> list[Region]:
        return await self.repository.search(query, limit=limit)
