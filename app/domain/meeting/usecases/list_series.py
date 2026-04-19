from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import MeetingSeries
from app.domain.meeting.service import MeetingSeriesService


@dataclass
class ListSeriesByHostUseCase:
    """호스트별 정기 모임 시리즈 목록 조회."""

    session: AsyncSession

    async def execute(
        self, host_id: str, *, offset: int = 0, limit: int = 20
    ) -> list[MeetingSeries]:
        return await MeetingSeriesService(self.session).list_by_host(
            host_id, offset=offset, limit=limit
        )


def list_series_by_host_use_case(
    session: AsyncSessionDep,
) -> ListSeriesByHostUseCase:
    return ListSeriesByHostUseCase(session=session)


ListSeriesByHostUseCaseDep = Annotated[
    ListSeriesByHostUseCase, Depends(list_series_by_host_use_case)
]
