from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import Meeting, MeetingSeries
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
    3. is_recurring=true 면 MeetingSeries + 첫 N 회차 Meeting 을 원자적으로 생성
       (요청된 meeting_date 와 일치하는 회차를 첫 Meeting 으로 반환)
    4. 아니면 단일 Meeting 을 생성
    """

    session: AsyncSession

    async def execute(self, host_id: str, data: MeetingCreate) -> Meeting:
        user_service = UserService(self.session)
        meeting_service = MeetingService(self.session)

        await user_service.get_by_id(host_id)

        if data.region_id is not None:
            region_service = RegionService(self.session)
            await region_service.ensure_exists(data.region_id)

        if data.is_recurring:
            assert data.recurrence is not None  # 스키마 validator 가 보장
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
                frequency=data.recurrence.frequency,
                start_date=data.meeting_date,
                end_date=data.recurrence.end_date,
                meeting_time=data.meeting_time,
            )
            series = await MeetingSeriesService(self.session).create_with_occurrences(
                series
            )
            # 요청한 meeting_date 에 해당하는 회차(첫 회차)를 반환한다.
            # Series 가 참조할 수 있는 Meeting 들은 create_with_occurrences 가 방금
            # 영속화했으므로 selectin 으로 이미 로드된 상태.
            for meeting in series.meetings:
                if meeting.meeting_date == data.meeting_date:
                    return meeting
            # 방어적 fallback — 이론상 도달 불가.
            return series.meetings[0]

        meeting = Meeting(
            host_id=host_id,
            series_id=None,
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
            is_recurring=False,
        )
        return await meeting_service.create(meeting)


def create_meeting_use_case(session: AsyncSessionDep) -> CreateMeetingUseCase:
    return CreateMeetingUseCase(session=session)


CreateMeetingUseCaseDep = Annotated[CreateMeetingUseCase, Depends(create_meeting_use_case)]
