"""User SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from ulid import ULID

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.auth.models import AuthIdentity
    from app.domain.meeting.models import Meeting, MeetingParticipant


def _generate_ulid() -> str:
    return str(ULID())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=_generate_ulid,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    profile_image: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    job: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    notification_prefs: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # 인증: 로컬 로그인 해시 (OAuth-only 유저는 NULL)
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    auth_identities: Mapped[list["AuthIdentity"]] = relationship(
        "AuthIdentity",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    hosted_meetings: Mapped[list["Meeting"]] = relationship(
        "Meeting",
        back_populates="host",
        lazy="selectin",
    )

    participations: Mapped[list["MeetingParticipant"]] = relationship(
        "MeetingParticipant",
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"
