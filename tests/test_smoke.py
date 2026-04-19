"""Smoke tests — app is wired and reachable."""

from __future__ import annotations

from httpx import AsyncClient


async def test_root_ok(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert "message" in body


async def test_docs_ok(client: AsyncClient) -> None:
    resp = await client.get("/docs")
    assert resp.status_code == 200


async def test_health_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "healthy"
    assert body.get("service") == "gakhalmo-api"
