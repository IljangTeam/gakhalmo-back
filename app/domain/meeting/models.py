"""Meeting SQLAlchemy models."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from ulid import ULID

from app.core.database import Base
from app.domain.meeting.enums import (
    Goal,
    MeetingMode,
    MeetingStatus,
    ParticipantStatus,
    RecurrenceFrequency,
)

if TYPE_CHECKING:
    from app.domain.regions.models import Region
    from app.domain.user.models import User


def _generate_ulid() -> str:
    return str(ULID())


class MeetingSeries(Base):
    __tablename__ = "meeting_series"

    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=_generate_ulid,
    )
    host_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    mode: Mapped[MeetingMode] = mapped_column(
        Enum(MeetingMode, name="meeting_mode", native_enum=False, length=32),
        nullable=False,
    )
    region_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("regions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    goal: Mapped[Goal] = mapped_column(
        Enum(Goal, name="meeting_goal", native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False)

    frequency: Mapped[RecurrenceFrequency] = mapped_column(
        Enum(
            RecurrenceFrequency,
            name="meeting_recurrence_frequency",
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    meeting_time: Mapped[time] = mapped_column(Time, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    host: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )
    region: Mapped["Region | None"] = relationship(
        "Region",
        lazy="selectin",
    )
    meetings: Mapped[list["Meeting"]] = relationship(
        "Meeting",
        back_populates="series",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "max_participants BETWEEN 2 AND 8",
            name="ck_meeting_series_max_participants_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<MeetingSeries(id={self.id}, title={self.title})>"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=_generate_ulid,
    )
    host_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    series_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("meeting_series.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    mode: Mapped[MeetingMode] = mapped_column(
        Enum(MeetingMode, name="meeting_mode", native_enum=False, length=32),
        nullable=False,
    )
    region_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("regions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    meeting_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meeting_time: Mapped[time] = mapped_column(Time, nullable=False)

    goal: Mapped[Goal] = mapped_column(
        Enum(Goal, name="meeting_goal", native_enum=False, length=32),
        nullable=False,
        index=True,
    )

    max_participants: Mapped[int] = mapped_column(Integer, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_recurring: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, name="meeting_status", native_enum=False, length=32),
        nullable=False,
        default=MeetingStatus.RECRUITING,
        server_default=MeetingStatus.RECRUITING.value,
        index=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    active_guard: Mapped[str] = mapped_column(
        String(26),
        nullable=False,
        default="",
        server_default=text("''"),
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

    host: Mapped["User"] = relationship(
        "User",
        back_populates="hosted_meetings",
        lazy="selectin",
    )
    region: Mapped["Region | None"] = relationship(
        "Region",
        lazy="selectin",
    )
    series: Mapped["MeetingSeries | None"] = relationship(
        "MeetingSeries",
        back_populates="meetings",
        lazy="selectin",
    )
    participants: Mapped[list["MeetingParticipant"]] = relationship(
        "MeetingParticipant",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "max_participants BETWEEN 2 AND 8",
            name="ck_meetings_max_participants_range",
        ),
        Index("ix_meetings_date_time", "meeting_date", "meeting_time"),
        Index(
            "ix_meetings_status_region_date",
            "status",
            "region_id",
            "meeting_date",
        ),
        UniqueConstraint(
            "host_id",
            "meeting_date",
            "meeting_time",
            "active_guard",
            name="uq_meetings_host_slot_active",
        ),
    )

    def __repr__(self) -> str:
        return f"<Meeting(id={self.id}, title={self.title})>"


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

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
    user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ParticipantStatus] = mapped_column(
        Enum(
            ParticipantStatus,
            name="meeting_participant_status",
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=ParticipantStatus.PENDING,
        server_default=ParticipantStatus.PENDING.value,
        index=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="participants",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="participations",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "user_id",
            name="uq_meeting_participants_meeting_user",
        ),
    )

    def __repr__(self) -> str:
        return f"<MeetingParticipant(meeting={self.meeting_id}, user={self.user_id})>"
