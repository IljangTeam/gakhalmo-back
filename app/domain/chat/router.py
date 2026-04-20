"""Chat API router."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.dependencies import AsyncSessionDep
from app.domain.auth.dependencies import CurrentUserDep
from app.domain.chat.schemas import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatRoomResponse,
)
from app.domain.chat.service import ChatService
from app.domain.chat.ws_hub import hub
from app.domain.notification.enums import NotificationType
from app.domain.notification.service import NotificationService
from app.domain.user.service import UserService

router = APIRouter(prefix="/chat", tags=["Chat"])


async def _msg_to_response(session, msg) -> ChatMessageResponse:
    user = await UserService(session).get_by_id(msg.user_id)
    return ChatMessageResponse.model_validate(
        {
            "id": msg.id,
            "room_id": msg.room_id,
            "user": user,
            "content": msg.content,
            "created_at": msg.created_at,
        }
    )


@router.get(
    "/rooms",
    response_model=list[ChatRoomResponse],
    summary="내가 참여한 채팅방 목록",
)
async def list_chat_rooms(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> list[ChatRoomResponse]:
    svc = ChatService(session)
    user_svc = UserService(session)
    rooms = await svc.list_rooms_for_user(current_user.id)

    out: list[ChatRoomResponse] = []
    for room in rooms:
        participants_rows = await svc.repository.list_participants(room.id)
        participants = [await user_svc.get_by_id(p.user_id) for p in participants_rows]
        last = await svc.repository.last_message(room.id)
        last_resp = await _msg_to_response(session, last) if last is not None else None
        unread = await svc.repository.count_unread(room.id, current_user.id)
        out.append(
            ChatRoomResponse.model_validate(
                {
                    "id": room.id,
                    "meeting_id": room.meeting_id,
                    "participants": participants,
                    "unread": unread,
                    "last_message": last_resp,
                    "created_at": room.created_at,
                }
            )
        )
    return out


@router.get(
    "/rooms/{room_id}/messages",
    response_model=list[ChatMessageResponse],
    summary="채팅방 메시지 목록 (최신순)",
)
async def list_messages(
    room_id: str,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[ChatMessageResponse]:
    svc = ChatService(session)
    messages = await svc.list_messages(room_id, current_user.id, offset=offset, limit=limit)
    out: list[ChatMessageResponse] = []
    for m in messages:
        out.append(await _msg_to_response(session, m))
    return out


@router.post(
    "/rooms/{room_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채팅방에 메시지 전송",
)
async def send_message(
    room_id: str,
    data: ChatMessageCreate,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> ChatMessageResponse:
    svc = ChatService(session)
    message = await svc.send_message(room_id, current_user.id, data.content)
    resp = await _msg_to_response(session, message)

    # 참여자 전원에게 알림 — 본인 제외
    participants = await svc.repository.list_participants(room_id)
    notif_svc = NotificationService(session)
    for p in participants:
        if p.user_id == current_user.id:
            continue
        await notif_svc.create(
            user_id=p.user_id,
            type=NotificationType.NEW_MESSAGE,
            payload={
                "room_id": room_id,
                "message_id": message.id,
                "from_user_id": current_user.id,
                "from_user_name": current_user.name,
                "preview": data.content[:80],
            },
        )

    # 실시간 WS broadcast (연결된 사용자에게만)
    await hub.broadcast_to_room(
        room_id=room_id,
        participants=[p.user_id for p in participants],
        payload={
            "event": "new_message",
            "message": {
                "id": message.id,
                "room_id": room_id,
                "user_id": current_user.id,
                "user_name": current_user.name,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            },
        },
    )

    return resp


@router.post(
    "/rooms/{room_id}/read",
    summary="채팅방 읽음 처리",
)
async def mark_room_read(
    room_id: str,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> dict[str, str]:
    svc = ChatService(session)
    participant = await svc.mark_read(room_id, current_user.id)
    return {"room_id": room_id, "last_read_at": participant.last_read_at.isoformat()}
