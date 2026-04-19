from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import MeetingParticipant
from app.domain.meeting.service import MeetingService
from app.domain.user.service import UserService


@dataclass
class JoinMeetingUseCase:
    """모임 참여 유스케이스.

    처리 흐름:
    1. 사용자 존재 검증
    2. MeetingService.join_with_lock — 행 잠금 내에서 상태/중복/정원 검증 후 INSERT
    """

    session: AsyncSession

    async def execute(self, meeting_id: str, user_id: str) -> MeetingParticipant:
        await UserService(self.session).get_by_id(user_id)
        return await MeetingService(self.session).join_with_lock(meeting_id, user_id)


def join_meeting_use_case(session: AsyncSessionDep) -> JoinMeetingUseCase:
    return JoinMeetingUseCase(session=session)


JoinMeetingUseCaseDep = Annotated[JoinMeetingUseCase, Depends(join_meeting_use_case)]
