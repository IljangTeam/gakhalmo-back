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

    async def get_by_full_name_prefixes(
        self, prefixes: list[str]
    ) -> list[Region]:
        """주어진 full_name 접미사/전체 일치 각각에 대해 가장 상위 1건만 반환.

        입력 순서를 유지하며 (프리셋 순서대로 노출), 매칭되지 않는 항목은 건너뛴다.
        """
        matched: list[Region] = []
        for prefix in prefixes:
            pattern = f"%{prefix}%"
            row = await self.session.execute(
                select(Region)
                .where(Region.full_name.ilike(pattern))
                .order_by(Region.full_name.asc())
                .limit(1)
            )
            region = row.scalar_one_or_none()
            if region is not None:
                matched.append(region)
        return matched
