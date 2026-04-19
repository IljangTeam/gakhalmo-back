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
    series_id: str | None = Field(None, description="소속 정기 모임 시리즈 ID")

    @model_validator(mode="after")
    def _validate_offline_fields(self) -> "MeetingCreate":
        if self.mode is MeetingMode.OFFLINE:
            if self.region_id is None:
                raise ValueError("오프라인 모임은 지역(region_id)이 필요합니다.")
            if not self.location_name:
                raise ValueError("오프라인 모임은 장소(location_name)가 필요합니다.")
        else:
            self.region_id = None
            self.location_name = None
            self.location_address = None
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
    is_recurring: bool | None = None
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


# ========== MeetingSeries ==========


class MeetingSeriesBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="시리즈 제목")
    description: str | None = Field(None, max_length=2000)
    mode: MeetingMode
    region_id: int | None = None
    location_name: str | None = Field(None, max_length=255)
    location_address: str | None = Field(None, max_length=500)
    goal: Goal
    max_participants: int = Field(..., ge=2, le=8)
    frequency: RecurrenceFrequency
    start_date: date
    end_date: date | None = None
    meeting_time: time


class MeetingSeriesCreateRequest(MeetingSeriesBase):
    @model_validator(mode="after")
    def _validate(self) -> "MeetingSeriesCreateRequest":
        if self.mode is MeetingMode.OFFLINE:
            if self.region_id is None:
                raise ValueError("오프라인 시리즈는 지역(region_id)이 필요합니다.")
            if not self.location_name:
                raise ValueError("오프라인 시리즈는 장소(location_name)가 필요합니다.")
        else:
            self.region_id = None
            self.location_name = None
            self.location_address = None

        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("종료일은 시작일 이후여야 합니다.")
        return self


class MeetingSeriesUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    mode: MeetingMode | None = None
    region_id: int | None = None
    location_name: str | None = Field(None, max_length=255)
    location_address: str | None = Field(None, max_length=500)
    goal: Goal | None = None
    max_participants: int | None = Field(None, ge=2, le=8)
    frequency: RecurrenceFrequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    meeting_time: time | None = None
    is_active: bool | None = None


class MeetingSeriesResponse(BaseModel):
    id: str
    title: str
    description: str | None
    mode: MeetingMode
    region: RegionSummary | None
    location_name: str | None
    location_address: str | None
    goal: Goal
    max_participants: int
    frequency: RecurrenceFrequency
    start_date: date
    end_date: date | None
    meeting_time: time
    is_active: bool
    host: UserSummary
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
