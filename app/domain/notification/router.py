"""Notification API router."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.dependencies import AsyncSessionDep
from app.domain.auth.dependencies import CurrentUserDep
from app.domain.notification.schemas import (
    NotificationResponse,
    UnreadCountResponse,
)
from app.domain.notification.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="내 알림 목록",
)
async def list_notifications(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False, description="읽지 않은 항목만 조회"),
) -> list[NotificationResponse]:
    service = NotificationService(session)
    rows = await service.list_for_user(
        current_user.id, offset=offset, limit=limit, unread_only=unread_only
    )
    return [NotificationResponse.model_validate(r) for r in rows]


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="읽지 않은 알림 개수",
)
async def unread_count(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> UnreadCountResponse:
    service = NotificationService(session)
    n = await service.count_unread(current_user.id)
    return UnreadCountResponse(unread=n)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="알림 읽음 처리",
)
async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> NotificationResponse:
    service = NotificationService(session)
    notification = await service.mark_read(notification_id, current_user.id)
    return NotificationResponse.model_validate(notification)


@router.post(
    "/read-all",
    summary="모든 알림 읽음 처리",
)
async def mark_all_read(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> dict[str, int]:
    service = NotificationService(session)
    updated = await service.mark_all_read(current_user.id)
    return {"updated": updated}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="알림 삭제",
)
async def delete_notification(
    notification_id: str,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> None:
    service = NotificationService(session)
    await service.delete(notification_id, current_user.id)
