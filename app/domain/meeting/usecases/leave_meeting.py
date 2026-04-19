from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.service import MeetingService


@dataclass
class LeaveMeetingUseCase:
    """모임 탈퇴 유스케이스.

    MeetingService.leave — 행 잠금 내에서 권한/참여 검증 후 DELETE.
    """

    session: AsyncSession

    async def execute(self, meeting_id: str, user_id: str) -> None:
        await MeetingService(self.session).leave(meeting_id, user_id)


def leave_meeting_use_case(session: AsyncSessionDep) -> LeaveMeetingUseCase:
    return LeaveMeetingUseCase(session=session)


LeaveMeetingUseCaseDep = Annotated[LeaveMeetingUseCase, Depends(leave_meeting_use_case)]
