from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.models import MeetingParticipant
from app.domain.meeting.service import MeetingService


@dataclass
class ApproveParticipantUseCase:
    """참여 승인 유스케이스 (호스트 전용).

    MeetingService.approve_participant 호출 — 호스트 검증/정원 재검증 후
    상태를 APPROVED로 전환하고 decided_at을 기록.
    """

    session: AsyncSession

    async def execute(
        self,
        meeting_id: str,
        participant_id: str,
        host_user_id: str,
    ) -> MeetingParticipant:
        return await MeetingService(self.session).approve_participant(
            meeting_id, participant_id, host_user_id
        )


def approve_participant_use_case(
    session: AsyncSessionDep,
) -> ApproveParticipantUseCase:
    return ApproveParticipantUseCase(session=session)


ApproveParticipantUseCaseDep = Annotated[
    ApproveParticipantUseCase, Depends(approve_participant_use_case)
]
