"""In-memory WebSocket hub — 단일 pod 전제의 최소 실시간 전달.

제한:
- replicas > 1 로 스케일 아웃하면 pod 간 메시지 전파 불가 → Redis pub/sub 등으로 확장 필요.
- MVP 단계에서는 replicas=1 로 충분하다.
- 연결 끊김 감지는 WebSocket 쪽에서 수행하며 hub 는 dict 관리만 담당.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionHub:
    """user_id 별 활성 WebSocket 연결을 보관하고 broadcast 를 제공한다."""

    def __init__(self) -> None:
        self._clients: dict[str, set["WebSocket"]] = {}
        self._lock = asyncio.Lock()

    async def register(self, user_id: str, ws: "WebSocket") -> None:
        async with self._lock:
            self._clients.setdefault(user_id, set()).add(ws)
        logger.info("ws connected user=%s total=%d", user_id, len(self._clients[user_id]))

    async def unregister(self, user_id: str, ws: "WebSocket") -> None:
        async with self._lock:
            conns = self._clients.get(user_id)
            if conns is None:
                return
            conns.discard(ws)
            if not conns:
                self._clients.pop(user_id, None)

    async def broadcast_to_users(self, user_ids: list[str], payload: dict) -> None:
        """user_ids 에 속한 모든 연결에 payload 전송. 끊어진 연결은 silently 제거."""
        async with self._lock:
            targets: list[tuple[str, "WebSocket"]] = []
            for uid in user_ids:
                for ws in self._clients.get(uid, set()):
                    targets.append((uid, ws))

        for uid, ws in targets:
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.warning("ws send failed user=%s err=%s — dropping", uid, exc)
                await self.unregister(uid, ws)

    async def broadcast_to_room(
        self, *, room_id: str, participants: list[str], payload: dict
    ) -> None:
        """Chat room 참여자 중 연결된 사람에게만 전송. room_id 는 로그/디버그용."""
        logger.debug("broadcast room=%s participants=%d", room_id, len(participants))
        await self.broadcast_to_users(participants, payload)


# 모듈 레벨 싱글턴 — FastAPI 모든 라우터/핸들러가 공유.
hub = ConnectionHub()
