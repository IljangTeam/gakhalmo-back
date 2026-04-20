"""Review + MeetingAttendance SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from ulid import ULID

from app.core.database import Base
from app.domain.review.enums import AttendanceStatus


def _generate_ulid() -> str:
    return str(ULID())


class Review(Base):
    """모임 종료 후, 한 참여자가 다른 참여자(호스트 포함)에게 남기는 회고/평가.

    같은 (meeting, reviewer, reviewee) 조합은 한 번만 가능 (UNIQUE).
    rating 은 1~5 범위.
    """

    __tablename__ = "reviews"

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
    reviewer_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewee_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "reviewer_id",
            "reviewee_id",
            name="uq_reviews_triplet",
        ),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),
    )


class MeetingAttendance(Base):
    """호스트가 모임 종료 후 각 참여자의 출석/노쇼 여부를 마킹.

    같은 (meeting, user) 는 한 번만 기록. 출석률 계산에 사용.
    """

    __tablename__ = "meeting_attendances"

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
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(
            AttendanceStatus,
            name="attendance_status",
            native_enum=False,
            length=20,
        ),
        nullable=False,
    )
    marked_by: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    marked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "meeting_id", "user_id", name="uq_attendance_meeting_user"
        ),
    )
