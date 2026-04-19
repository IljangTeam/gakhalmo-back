"""AuthIdentity SQLAlchemy model.

한 User는 여러 AuthIdentity를 가질 수 있다 (로컬 + 구글 병행 허용).
(provider, provider_user_id) 조합은 전역 유일.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from ulid import ULID

from app.core.database import Base
from app.domain.auth.enums import AuthProvider

if TYPE_CHECKING:
    from app.domain.user.models import User


def _generate_ulid() -> str:
    return str(ULID())


class AuthIdentity(Base):
    __tablename__ = "auth_identities"

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
    provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, name="auth_provider", native_enum=False, length=32),
        nullable=False,
    )
    # 외부 제공자의 사용자 식별자 (Google sub / 로컬은 email 재사용).
    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # provider가 공개한 이메일. 로컬의 경우 User.email과 동일.
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    user: Mapped["User"] = relationship(
        "User",
        back_populates="auth_identities",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_auth_identity_provider_user",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AuthIdentity(id={self.id}, user_id={self.user_id}, "
            f"provider={self.provider.value})>"
        )
