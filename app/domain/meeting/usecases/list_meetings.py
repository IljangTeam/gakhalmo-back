from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.meeting.enums import Goal, MeetingMode, MeetingStatus
from app.domain.meeting.models import Meeting
from app.domain.meeting.service import MeetingService


@dataclass
class ListMeetingsUseCase:
    """필터 기반 모임 목록 조회."""

    session: AsyncSession

    async def execute(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        mode: MeetingMode | None = None,
        region_id: int | None = None,
        goal: Goal | None = None,
        status: MeetingStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Meeting]:
        service = MeetingService(self.session)
        return await service.list(
            offset=offset,
            limit=limit,
            mode=mode,
            region_id=region_id,
            goal=goal,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )


@dataclass
class ListMeetingsByHostUseCase:
    """호스트별 모임 목록 조회."""

    session: AsyncSession

    async def execute(
        self, host_id: str, *, offset: int = 0, limit: int = 20
    ) -> list[Meeting]:
        service = MeetingService(self.session)
        return await service.list_by_host(host_id, offset=offset, limit=limit)


@dataclass
class ListMeetingsByParticipantUseCase:
    """참여자별 모임 목록 조회."""

    session: AsyncSession

    async def execute(
        self, user_id: str, *, offset: int = 0, limit: int = 20
    ) -> list[Meeting]:
        service = MeetingService(self.session)
        return await service.list_by_participant(user_id, offset=offset, limit=limit)


def list_meetings_use_case(session: AsyncSessionDep) -> ListMeetingsUseCase:
    return ListMeetingsUseCase(session=session)


def list_meetings_by_host_use_case(
    session: AsyncSessionDep,
) -> ListMeetingsByHostUseCase:
    return ListMeetingsByHostUseCase(session=session)


def list_meetings_by_participant_use_case(
    session: AsyncSessionDep,
) -> ListMeetingsByParticipantUseCase:
    return ListMeetingsByParticipantUseCase(session=session)


ListMeetingsUseCaseDep = Annotated[ListMeetingsUseCase, Depends(list_meetings_use_case)]
ListMeetingsByHostUseCaseDep = Annotated[
    ListMeetingsByHostUseCase, Depends(list_meetings_by_host_use_case)
]
ListMeetingsByParticipantUseCaseDep = Annotated[
    ListMeetingsByParticipantUseCase, Depends(list_meetings_by_participant_use_case)
]
