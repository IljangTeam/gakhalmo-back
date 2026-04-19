from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import Meeting
from app.domain.meeting.schemas import MeetingCreate
from app.domain.meeting.service import MeetingService, MeetingSeriesService
from app.domain.regions.service import RegionService
from app.domain.user.service import UserService


@dataclass
class CreateMeetingUseCase:
    """모임 생성 유스케이스.

    처리 흐름:
    1. 호스트 존재 검증
    2. (오프라인인 경우) 지역 FK 유효성 검증
    3. Meeting 엔티티 생성
    4. 영속화
    """

    session: AsyncSession

    async def execute(self, host_id: str, data: MeetingCreate) -> Meeting:
        user_service = UserService(self.session)
        meeting_service = MeetingService(self.session)

        await user_service.get_by_id(host_id)

        if data.region_id is not None:
            region_service = RegionService(self.session)
            await region_service.ensure_exists(data.region_id)

        if data.series_id is not None:
            series_service = MeetingSeriesService(self.session)
            series = await series_service.get_by_id(data.series_id)
            series_service.ensure_host(series, host_id)

        meeting = Meeting(
            host_id=host_id,
            series_id=data.series_id,
            title=data.title,
            mode=data.mode,
            region_id=data.region_id,
            location_name=data.location_name,
            location_address=data.location_address,
            meeting_date=data.meeting_date,
            meeting_time=data.meeting_time,
            goal=data.goal,
            max_participants=data.max_participants,
            description=data.description,
            is_recurring=data.is_recurring,
        )
        return await meeting_service.create(meeting)


def create_meeting_use_case(session: AsyncSessionDep) -> CreateMeetingUseCase:
    return CreateMeetingUseCase(session=session)


CreateMeetingUseCaseDep = Annotated[CreateMeetingUseCase, Depends(create_meeting_use_case)]
