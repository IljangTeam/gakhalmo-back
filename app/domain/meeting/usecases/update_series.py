from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.core.exceptions import ConflictError
from app.domain.meeting.enums import MeetingMode
from app.domain.meeting.models import MeetingSeries
from app.domain.meeting.schemas import MeetingSeriesUpdateRequest
from app.domain.meeting.service import MeetingSeriesService
from app.domain.regions.service import RegionService


@dataclass
class UpdateSeriesUseCase:
    """정기 모임 시리즈 수정 유스케이스.

    처리 흐름:
    1. 시리즈 조회 + 호스트 권한 검증
    2. (region_id 변경 시) FK 유효성 검증
    3. 변경 필드 적용 + 모드 일관성 검증
    """

    session: AsyncSession

    async def execute(
        self,
        series_id: str,
        host_id: str,
        data: MeetingSeriesUpdateRequest,
    ) -> MeetingSeries:
        service = MeetingSeriesService(self.session)
        series = await service.get_by_id(series_id)
        service.ensure_host(series, host_id)

        update_data = data.model_dump(exclude_unset=True)

        if "region_id" in update_data and update_data["region_id"] is not None:
            await RegionService(self.session).ensure_exists(update_data["region_id"])

        for field, value in update_data.items():
            setattr(series, field, value)

        if series.end_date is not None and series.end_date < series.start_date:
            raise ConflictError(detail="종료일은 시작일 이후여야 합니다.")

        if series.mode is MeetingMode.OFFLINE:
            if series.region_id is None or not series.location_name:
                raise ConflictError(
                    detail="오프라인 시리즈는 지역과 장소가 필요합니다.",
                )
        else:
            series.region_id = None
            series.location_name = None
            series.location_address = None

        return await service.update(series)


def update_series_use_case(session: AsyncSessionDep) -> UpdateSeriesUseCase:
    return UpdateSeriesUseCase(session=session)


UpdateSeriesUseCaseDep = Annotated[
    UpdateSeriesUseCase, Depends(update_series_use_case)
]
