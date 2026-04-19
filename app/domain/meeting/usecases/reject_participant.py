from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import MeetingParticipant
from app.domain.meeting.service import MeetingService


@dataclass
class RejectParticipantUseCase:
    """참여 거절 유스케이스 (호스트 전용)."""

    session: AsyncSession

    async def execute(
        self,
        meeting_id: str,
        participant_id: str,
        host_user_id: str,
    ) -> MeetingParticipant:
        return await MeetingService(self.session).reject_participant(
            meeting_id, participant_id, host_user_id
        )


def reject_participant_use_case(
    session: AsyncSessionDep,
) -> RejectParticipantUseCase:
    return RejectParticipantUseCase(session=session)


RejectParticipantUseCaseDep = Annotated[
    RejectParticipantUseCase, Depends(reject_participant_use_case)
]
