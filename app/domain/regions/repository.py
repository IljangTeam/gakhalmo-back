"""Region repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.regions.models import Region


class RegionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, region_id: int) -> Region | None:
        result = await self.session.execute(
            select(Region).where(Region.id == region_id)
        )
        return result.scalar_one_or_none()

    async def search(self, query: str, *, limit: int = 20) -> list[Region]:
        """full_name ILIKE 검색 (당근처럼 지역 자동완성용)."""
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(Region)
            .where(Region.full_name.ilike(pattern))
            .order_by(Region.full_name.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
