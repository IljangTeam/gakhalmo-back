from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.service import MeetingSeriesService


@dataclass
class DeleteSeriesUseCase:
    """정기 모임 시리즈 삭제 유스케이스 (소프트 삭제).

    series_id FK는 ON DELETE SET NULL이지만 소프트 삭제를 채택해
    이력/FK 무결성을 보존한다.
    """

    session: AsyncSession

    async def execute(self, series_id: str, host_id: str) -> None:
        service = MeetingSeriesService(self.session)
        series = await service.get_by_id(series_id)
        service.ensure_host(series, host_id)
        await service.delete(series)


def delete_series_use_case(session: AsyncSessionDep) -> DeleteSeriesUseCase:
    return DeleteSeriesUseCase(session=session)


DeleteSeriesUseCaseDep = Annotated[
    DeleteSeriesUseCase, Depends(delete_series_use_case)
]
