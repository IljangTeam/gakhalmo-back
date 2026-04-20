"""Notification SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from ulid import ULID

from app.core.database import Base
from app.domain.notification.enums import NotificationType


def _generate_ulid() -> str:
    return str(ULID())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=_generate_ulid,
    )
    user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            name="notification_type",
            native_enum=False,
            length=40,
        ),
        nullable=False,
        index=True,
    )
    # 자유 형식 payload — 각 type 별 부가 정보.
    # 예: {"meeting_id":"...", "participant_name":"..."}
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user={self.user_id}, type={self.type})>"
