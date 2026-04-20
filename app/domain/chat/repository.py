"""Chat repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat.models import ChatMessage, ChatParticipant, ChatRoom


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ========== Room ==========

    async def get_room_by_meeting(self, meeting_id: str) -> ChatRoom | None:
        result = await self.session.execute(
            select(ChatRoom).where(ChatRoom.meeting_id == meeting_id)
        )
        return result.scalar_one_or_none()

    async def get_room_by_id(self, room_id: str) -> ChatRoom | None:
        result = await self.session.execute(
            select(ChatRoom).where(ChatRoom.id == room_id)
        )
        return result.scalar_one_or_none()

    async def create_room(self, room: ChatRoom) -> ChatRoom:
        self.session.add(room)
        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def list_rooms_for_user(self, user_id: str) -> list[ChatRoom]:
        stmt = (
            select(ChatRoom)
            .join(ChatParticipant, ChatParticipant.room_id == ChatRoom.id)
            .where(ChatParticipant.user_id == user_id)
            .order_by(ChatRoom.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========== Participant ==========

    async def add_participant(self, participant: ChatParticipant) -> ChatParticipant:
        self.session.add(participant)
        await self.session.commit()
        await self.session.refresh(participant)
        return participant

    async def get_participant(
        self, room_id: str, user_id: str
    ) -> ChatParticipant | None:
        result = await self.session.execute(
            select(ChatParticipant).where(
                ChatParticipant.room_id == room_id,
                ChatParticipant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_participants(self, room_id: str) -> list[ChatParticipant]:
        result = await self.session.execute(
            select(ChatParticipant).where(ChatParticipant.room_id == room_id)
        )
        return list(result.scalars().all())

    # ========== Message ==========

    async def add_message(self, message: ChatMessage) -> ChatMessage:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_messages(
        self,
        room_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ChatMessage]:
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def last_message(self, room_id: str) -> ChatMessage | None:
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_unread(self, room_id: str, user_id: str) -> int:
        participant = await self.get_participant(room_id, user_id)
        if participant is None:
            return 0
        stmt = select(func.count(ChatMessage.id)).where(ChatMessage.room_id == room_id)
        if participant.last_read_at is not None:
            stmt = stmt.where(ChatMessage.created_at > participant.last_read_at)
        # 본인이 보낸 메시지는 unread 에서 제외.
        stmt = stmt.where(ChatMessage.user_id != user_id)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)
