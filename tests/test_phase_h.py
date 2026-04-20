"""Smoke tests for Phase H domains — Notification / Review+Attendance /
Connection / Chat / 24h leave policy / notification_prefs.

각 도메인의 핵심 golden path 만 짚는다. 엣지 케이스/동시성은 별도 스위트 필요.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.meeting.enums import ParticipantStatus
from app.domain.meeting.models import Meeting, MeetingParticipant


async def _register_login(client: AsyncClient, *, email: str, name: str = "Tester") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password1234", "name": name},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password1234"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _seed_meeting(
    db_session: AsyncSession,
    *,
    host_id: str,
    participant_id: str | None = None,
    meeting_date: date | None = None,
    meeting_time: time = time(14, 0),
) -> Meeting:
    """참여자 0 또는 1명짜리 오프라인 모임 seed. FK 제약 해결용으로 region_id 는 None."""
    meeting = Meeting(
        host_id=host_id,
        title="seed-meeting",
        mode="online",
        region_id=None,
        location_name=None,
        meeting_date=meeting_date or (datetime.now(UTC).date() + timedelta(days=7)),
        meeting_time=meeting_time,
        goal="공부",
        max_participants=4,
    )
    db_session.add(meeting)
    await db_session.commit()
    await db_session.refresh(meeting)
    if participant_id is not None:
        p = MeetingParticipant(
            meeting_id=meeting.id,
            user_id=participant_id,
            status=ParticipantStatus.APPROVED,
        )
        db_session.add(p)
        await db_session.commit()
    return meeting


# ---------- Notifications ----------


async def test_notifications_list_and_unread_count(client: AsyncClient) -> None:
    token = await _register_login(client, email="notif@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 초기 상태 — empty
    lst = await client.get("/api/v1/notifications", headers=headers)
    assert lst.status_code == 200
    assert lst.json() == []

    cnt = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert cnt.status_code == 200
    assert cnt.json() == {"unread": 0}


async def test_notifications_auth_required(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code in (401, 403)


# ---------- PATCH /auth/me with notification_prefs ----------


async def test_patch_me_notification_prefs(client: AsyncClient) -> None:
    token = await _register_login(client, email="prefs@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "notification_prefs": {
                "participant_pending": True,
                "new_message": False,
            }
        },
    )
    assert resp.status_code == 200
    assert resp.json()["notification_prefs"] == {
        "participant_pending": True,
        "new_message": False,
    }


# ---------- Reviews & Attendance ----------


async def test_review_self_review_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    host_token = await _register_login(client, email="host-r@example.com", name="Host")
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {host_token}"})
    host_id = me_resp.json()["id"]
    meeting = await _seed_meeting(db_session, host_id=host_id)

    resp = await client.post(
        f"/api/v1/meetings/{meeting.id}/reviews",
        headers={"Authorization": f"Bearer {host_token}"},
        json={"reviewee_id": host_id, "rating": 5},
    )
    assert resp.status_code == 400


async def test_attendance_rate_empty(client: AsyncClient) -> None:
    token = await _register_login(client, email="att@example.com")
    me = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).json()
    resp = await client.get(f"/api/v1/users/{me['id']}/attendance-rate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["attended"] == 0
    assert body["total_recorded"] == 0
    assert body["rate"] == 0.0


# ---------- Connection ----------


async def test_connection_request_accept_flow(client: AsyncClient) -> None:
    alice_t = await _register_login(client, email="c-alice@example.com", name="Alice")
    bob_t = await _register_login(client, email="c-bob@example.com", name="Bob")
    alice_id = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {alice_t}"})).json()["id"]
    bob_id = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bob_t}"})).json()["id"]

    # Alice → Bob 연결 요청
    req = await client.post(
        f"/api/v1/users/{bob_id}/connect",
        headers={"Authorization": f"Bearer {alice_t}"},
    )
    assert req.status_code == 201
    connection_id = req.json()["id"]
    assert req.json()["status"] == "pending"

    # Bob 수락
    acc = await client.post(
        f"/api/v1/connections/{connection_id}/accept",
        headers={"Authorization": f"Bearer {bob_t}"},
    )
    assert acc.status_code == 200
    assert acc.json()["status"] == "accepted"

    # Bob 기준 followers 조회 → Alice 포함
    lst = await client.get(
        f"/api/v1/users/{bob_id}/connections?direction=followers&status=accepted"
    )
    assert lst.status_code == 200
    assert any(c["follower"]["id"] == alice_id for c in lst.json())

    # Alice 에게 온 수락 알림 확인
    notifs = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {alice_t}"},
    )
    types = [n["type"] for n in notifs.json()]
    assert "connection_accepted" in types


async def test_connection_self_rejected(client: AsyncClient) -> None:
    token = await _register_login(client, email="self-c@example.com")
    me = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).json()
    resp = await client.post(
        f"/api/v1/users/{me['id']}/connect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ---------- 24h leave guard ----------


async def test_leave_blocked_within_24h(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    host_email = "guard-host@example.com"
    guest_email = "guard-guest@example.com"
    host_t = await _register_login(client, email=host_email, name="Host")
    guest_t = await _register_login(client, email=guest_email, name="Guest")
    host_me = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {host_t}"})).json()
    guest_me = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {guest_t}"})).json()

    # 내일 14시 모임, Guest 가 이미 APPROVED 상태로 포함되어 있음.
    tomorrow = (datetime.now(UTC) + timedelta(hours=6)).date()  # 24h 이내
    meeting = await _seed_meeting(
        db_session,
        host_id=host_me["id"],
        participant_id=guest_me["id"],
        meeting_date=tomorrow,
        meeting_time=time((datetime.now(UTC) + timedelta(hours=6)).hour, 0),
    )

    resp = await client.delete(
        f"/api/v1/meetings/{meeting.id}/participants/me",
        headers={"Authorization": f"Bearer {guest_t}"},
    )
    assert resp.status_code == 403
    assert "24" in resp.json()["detail"]


# ---------- Chat (room 생성 smoke) ----------


async def test_chat_send_forbidden_without_room(client: AsyncClient) -> None:
    token = await _register_login(client, email="chat-solo@example.com")
    # 존재하지 않는 room
    resp = await client.post(
        "/api/v1/chat/rooms/01KPXXXXXXXXXXXXXXXXXXXXXX/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "hi"},
    )
    assert resp.status_code in (403, 404)
