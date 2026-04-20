"""Chat SQLAlchemy models.

설계:
- 한 Meeting 당 최대 한 개의 ChatRoom (UNIQUE meeting_id).
- 참여 승인 시점(approve_participant) 에 ChatRoom + 호스트 ChatParticipant 가 lazily 생성,
  승인된 참여자도 같은 타이밍에 ChatParticipant 로 등록.
- 메시지는 append-only. 읽음 처리는 ChatParticipant.last_read_at 으로 관리.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from ulid import ULID

from app.core.database import Base


def _generate_ulid() -> str:
    return str(ULID())


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=_generate_ulid,
    )
    meeting_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("meeting_id", name="uq_chat_rooms_meeting"),
    )


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=_generate_ulid,
    )
    room_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_chat_participants_pair"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=_generate_ulid,
    )
    room_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
