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


async def test_popular_endpoint_respects_preset_order(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """/regions/popular 는 POPULAR_PREFIXES 순서대로 매칭된 지역만 반환한다.

    세션 스코프 DB 에 기존 시드가 있을 수 있어, 여기서는 두 프리셋 매칭 row 만
    추가로 유니크 full_name 으로 seed 하고 응답 내 순서 조건만 검증한다.
    """
    # 프리셋에 걸리는 구분 키워드를 포함하되 유니크하게 — 다른 테스트 시드와 충돌 방지.
    a = await _seed_region(
        db_session,
        sido="서울특별시",
        sigungu="마포구",
        name="서교동",
        full_name="테스트-서울특별시 마포구 서교동",
    )
    b = await _seed_region(
        db_session,
        sido="서울특별시",
        sigungu="종로구",
        name="관철동",
        full_name="테스트-서울특별시 종로구 관철동",
    )

    resp = await client.get("/api/v1/regions/popular")
    assert resp.status_code == 200
    body = resp.json()
    # 응답 안에서 '서교동' 매칭이 '관철동' 매칭보다 먼저 등장해야 한다 (프리셋 순서).
    full_names = [item["full_name"] for item in body]
    a_idx = next(
        i for i, fn in enumerate(full_names) if "마포구 서교동" in fn
    )
    b_idx = next(
        i for i, fn in enumerate(full_names) if "종로구 관철동" in fn
    )
    assert a_idx < b_idx, f"프리셋 순서 위반: {full_names}"
    # 시드된 row 둘 다 응답에 포함되어야 한다.
    assert any(item["id"] == a.id for item in body)
    assert any(item["id"] == b.id for item in body)
