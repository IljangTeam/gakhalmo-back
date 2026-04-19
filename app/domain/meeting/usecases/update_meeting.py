from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.core.exceptions import ConflictError
from app.domain.meeting.enums import MeetingMode
from app.domain.meeting.models import Meeting
from app.domain.meeting.schemas import MeetingUpdate
from app.domain.meeting.service import MeetingService
from app.domain.regions.service import RegionService


@dataclass
class UpdateMeetingUseCase:
    """모임 정보 수정 유스케이스.

    처리 흐름:
    1. 기존 모임 조회
    2. 호스트 권한 검증
    3. (region_id 변경 시) FK 유효성 검증
    4. 변경 필드 적용
    5. 모드/정원 일관성 검증 후 영속화
    """

    session: AsyncSession

    async def execute(
        self,
        meeting_id: str,
        host_id: str,
        data: MeetingUpdate,
    ) -> Meeting:
        service = MeetingService(self.session)
        meeting = await service.get_by_id(meeting_id)
        service.ensure_host(meeting, host_id)

        update_data = data.model_dump(exclude_unset=True)

        if "region_id" in update_data and update_data["region_id"] is not None:
            region_service = RegionService(self.session)
            await region_service.ensure_exists(update_data["region_id"])

        for field, value in update_data.items():
            setattr(meeting, field, value)

        current_participants = await service.count_participants(meeting.id)
        if meeting.max_participants < current_participants:
            raise ConflictError(
                detail="최대 인원을 현재 참여 인원보다 적게 설정할 수 없습니다.",
            )

        if meeting.mode is MeetingMode.OFFLINE:
            if meeting.region_id is None or not meeting.location_name:
                raise ConflictError(
                    detail="오프라인 모임은 지역과 장소가 필요합니다.",
                )
        else:
            meeting.region_id = None
            meeting.location_name = None
            meeting.location_address = None

        return await service.update(meeting)


def update_meeting_use_case(session: AsyncSessionDep) -> UpdateMeetingUseCase:
    return UpdateMeetingUseCase(session=session)


UpdateMeetingUseCaseDep = Annotated[UpdateMeetingUseCase, Depends(update_meeting_use_case)]
