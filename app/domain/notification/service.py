"""Notification domain service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.notification.enums import NotificationType
from app.domain.notification.models import Notification
from app.domain.notification.repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = NotificationRepository(session)

    async def create(
        self,
        *,
        user_id: str,
        type: NotificationType,
        payload: dict | None = None,
    ) -> Notification:
        """내부 호출용 — 이벤트 훅에서 사용.

        예외를 던지지 않고 삼킨다 — 알림 생성 실패가 주된 비즈니스 흐름을 막으면 안 된다.
        (예: 모임 승인은 성공했는데 알림 실패 → 전체 rollback → 상위 로직 꼬임)
        대신 로그로만 기록. 현재는 최소 구현이라 예외를 위로 올린다; 추후 Redis/queue 기반
        비동기 전달이 붙으면 fire-and-forget 으로 바뀐다.
        """
        notification = Notification(user_id=user_id, type=type, payload=payload)
        return await self.repository.create(notification)

    async def list_for_user(
        self,
        user_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
        unread_only: bool = False,
    ) -> list[Notification]:
        return await self.repository.list_by_user(
            user_id, offset=offset, limit=limit, unread_only=unread_only
        )

    async def count_unread(self, user_id: str) -> int:
        return await self.repository.count_unread(user_id)

    async def mark_read(self, notification_id: str, user_id: str) -> Notification:
        notification = await self.repository.get_by_id(notification_id)
        if notification is None:
            raise NotFoundError(detail="알림을 찾을 수 없습니다.")
        if notification.user_id != user_id:
            raise ForbiddenError(detail="본인 알림만 조작할 수 있습니다.")
        if notification.read_at is not None:
            return notification  # 이미 읽음 처리됨 — idempotent
        return await self.repository.mark_read(notification)

    async def mark_all_read(self, user_id: str) -> int:
        return await self.repository.mark_all_read(user_id)

    async def delete(self, notification_id: str, user_id: str) -> None:
        notification = await self.repository.get_by_id(notification_id)
        if notification is None:
            raise NotFoundError(detail="알림을 찾을 수 없습니다.")
        if notification.user_id != user_id:
            raise ForbiddenError(detail="본인 알림만 삭제할 수 있습니다.")
        await self.repository.delete(notification)
