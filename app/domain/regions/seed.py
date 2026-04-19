"""regions.json → DB upsert."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.regions.models import Region

SEED_FILE = Path(__file__).parent / "seeds" / "regions.json"


async def seed_regions(session: AsyncSession, *, force: bool = False) -> int:
    """regions.json을 DB에 시드.

    기본은 테이블이 비어 있을 때만 삽입(최초 1회). 데이터를 강제로
    재적용하려면 force=True.
    """
    if not force:
        existing = await session.scalar(select(func.count()).select_from(Region))
        if existing:
            return 0

    with SEED_FILE.open(encoding="utf-8") as f:
        data: list[dict[str, str | None]] = json.load(f)

    if not data:
        return 0

    rows = [
        {
            "sido": r["sido"],
            "sigungu": r["sigungu"],
            "name": r["name"],
            "full_name": r["full_name"],
        }
        for r in data
    ]

    stmt = insert(Region).values(rows)
    stmt = stmt.on_duplicate_key_update(
        sido=stmt.inserted.sido,
        sigungu=stmt.inserted.sigungu,
        name=stmt.inserted.name,
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)
