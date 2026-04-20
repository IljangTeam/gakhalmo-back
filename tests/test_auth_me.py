"""PATCH /auth/me — 본인 프로필 수정 (tags, job, bio, name 포함)."""

from __future__ import annotations

from httpx import AsyncClient


async def _register_and_login(
    client: AsyncClient, *, email: str, password: str = "password1234"
) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Tester"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def test_patch_me_updates_tags_job_bio(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="me-patch@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "name": "수정된이름",
            "bio": "한 줄 소개",
            "job": "백엔드",
            "tags": ["#홍대", "#저녁", "#공부"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "수정된이름"
    assert body["bio"] == "한 줄 소개"
    assert body["job"] == "백엔드"
    assert body["tags"] == ["#홍대", "#저녁", "#공부"]

    # GET /me 로 재확인 — 영속 여부
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["name"] == "수정된이름"
    assert me_body["tags"] == ["#홍대", "#저녁", "#공부"]


async def test_patch_me_empty_tag_list_clears(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="me-clear@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"tags": ["#a", "#b"]},
    )
    resp = await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"tags": []},
    )
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


async def test_patch_me_unauthenticated_rejected(client: AsyncClient) -> None:
    resp = await client.patch(
        "/api/v1/auth/me",
        json={"name": "hi"},
    )
    assert resp.status_code in (401, 403)


async def test_patch_me_partial_leaves_other_fields(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="me-partial@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"bio": "원본", "job": "디자이너"},
    )
    resp = await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"job": "프론트엔드"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["job"] == "프론트엔드"
    assert body["bio"] == "원본"
