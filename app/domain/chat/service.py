"""Chat domain service."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.chat.models import ChatMessage, ChatParticipant, ChatRoom
from app.domain.chat.repository import ChatRepository


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ChatRepository(session)

    async def ensure_room_for_meeting(self, meeting_id: str) -> ChatRoom:
        """존재하지 않으면 생성, 있으면 재사용 (idempotent)."""
        room = await self.repository.get_room_by_meeting(meeting_id)
        if room is not None:
            return room
        room = ChatRoom(meeting_id=meeting_id)
        return await self.repository.create_room(room)

    async def ensure_participant(self, room_id: str, user_id: str) -> ChatParticipant:
        """참여자 row 가 없으면 생성 (idempotent)."""
        participant = await self.repository.get_participant(room_id, user_id)
        if participant is not None:
            return participant
        participant = ChatParticipant(room_id=room_id, user_id=user_id)
        return await self.repository.add_participant(participant)

    async def list_rooms_for_user(self, user_id: str) -> list[ChatRoom]:
        return await self.repository.list_rooms_for_user(user_id)

    async def _authorize(self, room_id: str, user_id: str) -> ChatRoom:
        room = await self.repository.get_room_by_id(room_id)
        if room is None:
            raise NotFoundError(detail="채팅방을 찾을 수 없습니다.")
        participant = await self.repository.get_participant(room_id, user_id)
        if participant is None:
            raise ForbiddenError(detail="채팅방 참여자가 아닙니다.")
        return room

    async def send_message(
        self, room_id: str, user_id: str, content: str
    ) -> ChatMessage:
        await self._authorize(room_id, user_id)
        message = ChatMessage(room_id=room_id, user_id=user_id, content=content)
        return await self.repository.add_message(message)

    async def list_messages(
        self,
        room_id: str,
        user_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ChatMessage]:
        await self._authorize(room_id, user_id)
        return await self.repository.list_messages(room_id, offset=offset, limit=limit)

    async def mark_read(self, room_id: str, user_id: str) -> ChatParticipant:
        await self._authorize(room_id, user_id)
        participant = await self.repository.get_participant(room_id, user_id)
        assert participant is not None  # _authorize 에서 검증됨
        participant.last_read_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(participant)
        return participant
