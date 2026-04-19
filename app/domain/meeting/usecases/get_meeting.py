from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import Meeting
from app.domain.meeting.service import MeetingService


@dataclass
class GetMeetingUseCase:
    """ID로 모임 조회."""

    session: AsyncSession

    async def execute(self, meeting_id: str) -> Meeting:
        service = MeetingService(self.session)
        return await service.get_by_id(meeting_id)


def get_meeting_use_case(session: AsyncSessionDep) -> GetMeetingUseCase:
    return GetMeetingUseCase(session=session)


GetMeetingUseCaseDep = Annotated[GetMeetingUseCase, Depends(get_meeting_use_case)]
