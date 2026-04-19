"""Region repository + endpoint round-trip."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.regions.models import Region
from app.domain.regions.repository import RegionRepository


async def _seed_region(
    db_session: AsyncSession,
    *,
    sido: str = "서울특별시",
    sigungu: str | None = "강남구",
    name: str = "역삼동",
    full_name: str = "서울특별시 강남구 역삼동",
) -> Region:
    region = Region(sido=sido, sigungu=sigungu, name=name, full_name=full_name)
    db_session.add(region)
    await db_session.commit()
    await db_session.refresh(region)
    return region


async def test_repository_roundtrip(db_session: AsyncSession) -> None:
    created = await _seed_region(db_session)
    assert created.id is not None

    repo = RegionRepository(db_session)
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.full_name == "서울특별시 강남구 역삼동"

    results = await repo.search("역삼")
    assert any(r.id == created.id for r in results)


async def test_search_endpoint(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    region = await _seed_region(
        db_session,
        sido="부산광역시",
        sigungu="해운대구",
        name="우동",
        full_name="부산광역시 해운대구 우동",
    )

    resp = await client.get("/api/v1/regions/search", params={"q": "우동"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert any(item["id"] == region.id for item in body)


async def test_get_region_by_id_found(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    region = await _seed_region(
        db_session,
        sido="경기도",
        sigungu="성남시 분당구",
        name="정자동",
        full_name="경기도 성남시 분당구 정자동",
    )

    resp = await client.get(f"/api/v1/regions/{region.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == region.id
    assert body["full_name"] == "경기도 성남시 분당구 정자동"


async def test_get_region_by_id_missing(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/regions/999999")
    assert resp.status_code == 404
