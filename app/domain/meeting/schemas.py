"""Meeting Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.meeting.enums import (
    Goal,
    MeetingMode,
    MeetingStatus,
    ParticipantStatus,
    RecurrenceFrequency,
)
from app.domain.regions.schemas import RegionSummary
from app.domain.user.schemas import UserSummary


class RecurrenceData(BaseModel):
    """is_recurring=true 일 때 내부적으로 Series 를 만들기 위한 부가 정보.

    `meeting_date` 를 Series.start_date 로, `meeting_time` 을 Series.meeting_time 으로
    승격시키므로 여기에는 시리즈 고유 정보(주기/종료일) 만 담는다.
    """

    frequency: RecurrenceFrequency = Field(..., description="반복 주기")
    end_date: date | None = Field(
        None,
        description="반복 종료일 (미지정 시 서버 기본 횟수 생성)",
    )


class MeetingBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="모임 제목")
    mode: MeetingMode = Field(..., description="온/오프라인 구분")
    region_id: int | None = Field(None, description="지역 ID (오프라인 필수, regions.id 참조)")
    location_name: str | None = Field(None, max_length=255, description="장소 이름")
    location_address: str | None = Field(None, max_length=500, description="장소 주소")
    meeting_date: date = Field(..., description="모임 날짜")
    meeting_time: time = Field(..., description="모임 시간")
    goal: Goal = Field(..., description="모임 목표")
    max_participants: int = Field(..., ge=2, le=8, description="최대 인원 (2-8)")
    description: str | None = Field(None, max_length=2000, description="모임 설명")
    is_recurring: bool = Field(False, description="정기 모임 여부")


class MeetingCreate(MeetingBase):
    """모임 생성 요청.

    정기 모임(`is_recurring=true`)이면 `recurrence` 가 필수이며, 서버 내부에서
    MeetingSeries 를 생성해 이 Meeting 을 첫 회차로 연결한다. 외부 API 로 Series 를
    직접 다루지 않는다 (내부 리소스).
    """

    recurrence: RecurrenceData | None = Field(
        None,
        description="is_recurring=true 일 때 필수 (주기/종료일)",
    )

    @model_validator(mode="after")
    def _validate(self) -> "MeetingCreate":
        if self.mode is MeetingMode.OFFLINE:
            if self.region_id is None:
                raise ValueError("오프라인 모임은 지역(region_id)이 필요합니다.")
            if not self.location_name:
                raise ValueError("오프라인 모임은 장소(location_name)가 필요합니다.")
        else:
            self.region_id = None
            self.location_name = None
            self.location_address = None

        if self.is_recurring and self.recurrence is None:
            raise ValueError(
                "is_recurring=true 이면 recurrence(frequency/end_date) 가 필요합니다."
            )
        if not self.is_recurring and self.recurrence is not None:
            raise ValueError(
                "is_recurring=false 면 recurrence 는 지정할 수 없습니다."
            )
        if (
            self.recurrence is not None
            and self.recurrence.end_date is not None
            and self.recurrence.end_date < self.meeting_date
        ):
            raise ValueError("recurrence.end_date 는 meeting_date 이후여야 합니다.")
        return self


class MeetingUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    mode: MeetingMode | None = None
    region_id: int | None = None
    location_name: str | None = Field(None, max_length=255)
    location_address: str | None = Field(None, max_length=500)
    meeting_date: date | None = None
    meeting_time: time | None = None
    goal: Goal | None = None
    max_participants: int | None = Field(None, ge=2, le=8)
    description: str | None = Field(None, max_length=2000)
    status: MeetingStatus | None = None


class MeetingParticipantResponse(BaseModel):
    id: str
    user: UserSummary
    status: ParticipantStatus
    decided_at: datetime | None = None
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Backwards-compatible alias so callers can refer to the participant
# schema by a shorter name without breaking existing imports.
ParticipantResponse = MeetingParticipantResponse


class ParticipantStatusUpdateRequest(BaseModel):
    """승인/거절 엔드포인트용 선택적 요청 바디."""

    reason: str | None = Field(
        None,
        max_length=500,
        description="결정 사유 (선택)",
    )


class MeetingResponse(BaseModel):
    id: str
    title: str
    mode: MeetingMode
    region: RegionSummary | None
    location_name: str | None
    location_address: str | None
    meeting_date: date
    meeting_time: time
    goal: Goal
    max_participants: int
    current_participants: int
    is_full: bool = Field(
        ...,
        description="current_participants >= max_participants 여부 (파생 필드)",
    )
    description: str | None
    is_recurring: bool
    status: MeetingStatus
    series_id: str | None
    host: UserSummary
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingDetailResponse(MeetingResponse):
    participants: list[MeetingParticipantResponse]
