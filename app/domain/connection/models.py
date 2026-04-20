"""Connection (follow/friend) SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from ulid import ULID

from app.core.database import Base
from app.domain.connection.enums import ConnectionStatus


def _generate_ulid() -> str:
    return str(ULID())


class Connection(Base):
    """팔로우/친구 관계.

    `follower_id` → `following_id` 방향. PENDING 은 요청한 상태, ACCEPTED 는 수락된 상태.
    쌍방 연결은 2개의 row (A→B + B→A) 로 표현한다 — 일방 팔로우도 가능하도록.
    """

    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=_generate_ulid,
    )
    follower_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    following_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(
            ConnectionStatus,
            name="connection_status",
            native_enum=False,
            length=20,
        ),
        nullable=False,
        default=ConnectionStatus.PENDING,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_connections_pair"),
    )
