"""Chat Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.user.schemas import UserSummary


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class ChatMessageResponse(BaseModel):
    id: str
    room_id: str
    user: UserSummary
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRoomResponse(BaseModel):
    id: str
    meeting_id: str
    participants: list[UserSummary]
    unread: int = Field(..., ge=0, description="현재 사용자 기준 미읽은 메시지 수")
    last_message: ChatMessageResponse | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
