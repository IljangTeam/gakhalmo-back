"""Notification Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.notification.enums import NotificationType


class NotificationCreate(BaseModel):
    """내부 사용용 — 이벤트 훅에서 호출. 외부 라우터엔 노출 안 됨."""

    user_id: str
    type: NotificationType
    payload: dict | None = None


class NotificationResponse(BaseModel):
    id: str
    type: NotificationType
    payload: dict | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    unread: int = Field(..., ge=0)
