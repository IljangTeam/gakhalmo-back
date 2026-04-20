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

    # 프리셋 지역 — 홍대/성수/강남/판교/종로 순. full_name 부분 일치로 resolve.
    # 데이터 설계(is_popular 컬럼) 까지 가지 않고 코드에서 관리 — 운영 요구사항 변경 시
    # 이 튜플만 수정하면 되며 마이그레이션은 불필요하다.
    POPULAR_PREFIXES: tuple[str, ...] = (
        "마포구 서교동",       # 홍대
        "성동구 성수동1가",    # 성수
        "강남구 역삼동",       # 강남
        "분당구 판교동",       # 판교
        "종로구 관철동",       # 종로
    )

    async def list_popular(self) -> list[Region]:
        """홈 피드/개설 폼에 노출되는 프리셋 지역 목록."""
        return await self.repository.get_by_full_name_prefixes(
            list(self.POPULAR_PREFIXES)
        )
