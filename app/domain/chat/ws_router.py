"""WebSocket endpoint: /api/v1/ws?token=...

- Access token 쿼리 파라미터로 인증 (브라우저 WebSocket API 가 헤더 삽입을 지원 안 함).
- 연결 유지 동안 해당 user_id 가 참여한 모든 채팅방의 새 메시지를 푸시받는다.
- 클라이언트가 메시지를 보내는 채널은 아님 — 메시지 전송은 HTTP POST /chat/rooms/{id}/messages.
  이 구조가 단순하고 auth/persistence 가 HTTP 계층에서 보장된다.
"""

from __future__ import annotations

import logging

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.core.security import TokenType, decode_token
from app.domain.chat.ws_hub import hub
from app.domain.user.repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="access_token (HTTPAuthorization 대체)"),
) -> None:
    # 토큰 검증 — HTTP /auth/me 와 동일 규칙.
    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS)
    except jwt.PyJWTError as exc:
        logger.info("ws auth failed: %s", exc)
        await websocket.close(code=4401)
        return

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        await websocket.close(code=4401)
        return

    # 활성 유저 검증 — DB 조회는 짧게.
    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get_by_id(user_id)
        if user is None or not user.is_active:
            await websocket.close(code=4401)
            return

    await websocket.accept()
    await hub.register(user_id, websocket)
    try:
        # 클라이언트가 보내는 메시지는 heartbeat(ping) 로만 간주하고 버린다.
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await hub.unregister(user_id, websocket)
