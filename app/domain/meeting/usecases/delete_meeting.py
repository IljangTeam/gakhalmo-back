from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.service import MeetingService


@dataclass
class DeleteMeetingUseCase:
    """모임 삭제 유스케이스.

    처리 흐름:
    1. 모임 조회
    2. 호스트 권한 검증
    3. 삭제
    """

    session: AsyncSession

    async def execute(self, meeting_id: str, host_id: str) -> None:
        service = MeetingService(self.session)
        meeting = await service.get_by_id(meeting_id)
        service.ensure_host(meeting, host_id)
        await service.delete(meeting)


def delete_meeting_use_case(session: AsyncSessionDep) -> DeleteMeetingUseCase:
    return DeleteMeetingUseCase(session=session)


DeleteMeetingUseCaseDep = Annotated[DeleteMeetingUseCase, Depends(delete_meeting_use_case)]
