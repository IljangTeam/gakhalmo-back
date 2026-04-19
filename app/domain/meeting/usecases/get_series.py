from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import MeetingSeries
from app.domain.meeting.service import MeetingSeriesService


@dataclass
class GetSeriesUseCase:
    """ID로 시리즈 조회."""

    session: AsyncSession

    async def execute(self, series_id: str) -> MeetingSeries:
        return await MeetingSeriesService(self.session).get_by_id(series_id)


def get_series_use_case(session: AsyncSessionDep) -> GetSeriesUseCase:
    return GetSeriesUseCase(session=session)


GetSeriesUseCaseDep = Annotated[GetSeriesUseCase, Depends(get_series_use_case)]
