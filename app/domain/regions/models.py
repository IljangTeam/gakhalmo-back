"""Region SQLAlchemy model (당근 스타일 읍/면/동/리 단위)."""

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    sido: Mapped[str] = mapped_column(String(40), nullable=False)
    sigungu: Mapped[str | None] = mapped_column(String(80), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)

    __table_args__ = (
        UniqueConstraint("full_name", name="uq_regions_full_name"),
        Index("ix_regions_sido_sigungu", "sido", "sigungu"),
        Index("ix_regions_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Region(full_name={self.full_name})>"
