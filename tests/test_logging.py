"""Request-ID middleware — header roundtrip + incoming value honoured."""

from __future__ import annotations

from httpx import AsyncClient


async def test_request_id_header_assigned(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    rid = resp.headers.get("X-Request-ID")
    assert rid
    # uuid.uuid4().hex → 32 hex chars.
    assert len(rid) == 32


async def test_request_id_header_honours_incoming(client: AsyncClient) -> None:
    incoming = "abc-123-test-rid"
    resp = await client.get("/health", headers={"X-Request-ID": incoming})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == incoming
