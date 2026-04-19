from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import MeetingSeries
from app.domain.meeting.schemas import MeetingSeriesCreateRequest
from app.domain.meeting.service import MeetingSeriesService
from app.domain.regions.service import RegionService
from app.domain.user.service import UserService


@dataclass
class CreateSeriesUseCase:
    """정기 모임 시리즈 생성 유스케이스.

    처리 흐름:
    1. 호스트 존재 검증
    2. (오프라인인 경우) 지역 FK 유효성 검증
    3. MeetingSeries + 첫 N회 Meeting 인스턴스 생성 (단일 트랜잭션)
    """

    session: AsyncSession

    async def execute(self, host_id: str, data: MeetingSeriesCreateRequest) -> MeetingSeries:
        await UserService(self.session).get_by_id(host_id)

        if data.region_id is not None:
            await RegionService(self.session).ensure_exists(data.region_id)

        series = MeetingSeries(
            host_id=host_id,
            title=data.title,
            description=data.description,
            mode=data.mode,
            region_id=data.region_id,
            location_name=data.location_name,
            location_address=data.location_address,
            goal=data.goal,
            max_participants=data.max_participants,
            frequency=data.frequency,
            start_date=data.start_date,
            end_date=data.end_date,
            meeting_time=data.meeting_time,
        )
        return await MeetingSeriesService(self.session).create_with_occurrences(series)


def create_series_use_case(session: AsyncSessionDep) -> CreateSeriesUseCase:
    return CreateSeriesUseCase(session=session)


CreateSeriesUseCaseDep = Annotated[CreateSeriesUseCase, Depends(create_series_use_case)]
