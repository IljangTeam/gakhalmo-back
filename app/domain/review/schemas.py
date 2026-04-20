"""Review + Attendance Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.review.enums import AttendanceStatus
from app.domain.user.schemas import UserSummary


class ReviewCreate(BaseModel):
    reviewee_id: str = Field(..., description="회고 대상 user_id")
    rating: int = Field(..., ge=1, le=5, description="1~5점")
    content: str | None = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    id: str
    meeting_id: str
    reviewer: UserSummary
    reviewee: UserSummary
    rating: int
    content: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceMarkRequest(BaseModel):
    status: AttendanceStatus


class AttendanceResponse(BaseModel):
    id: str
    meeting_id: str
    user_id: str
    status: AttendanceStatus
    marked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceRateResponse(BaseModel):
    user_id: str
    attended: int = Field(..., ge=0)
    total_recorded: int = Field(..., ge=0)
    rate: float = Field(..., ge=0, le=1, description="attended / total_recorded")
