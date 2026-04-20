"""Connection API router."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.dependencies import AsyncSessionDep
from app.domain.auth.dependencies import CurrentUserDep
from app.domain.connection.enums import ConnectionStatus
from app.domain.connection.schemas import ConnectionResponse
from app.domain.connection.service import ConnectionService
from app.domain.notification.enums import NotificationType
from app.domain.notification.service import NotificationService
from app.domain.user.service import UserService

router = APIRouter(tags=["Connections"])


async def _to_response(session, connection) -> ConnectionResponse:
    user_svc = UserService(session)
    follower = await user_svc.get_by_id(connection.follower_id)
    following = await user_svc.get_by_id(connection.following_id)
    return ConnectionResponse.model_validate(
        {
            "id": connection.id,
            "follower": follower,
            "following": following,
            "status": connection.status,
            "created_at": connection.created_at,
            "accepted_at": connection.accepted_at,
        }
    )


@router.post(
    "/users/{user_id}/connect",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="다른 사용자에게 연결 요청",
)
async def connect_user(
    user_id: str,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> ConnectionResponse:
    svc = ConnectionService(session)
    connection = await svc.request(current_user.id, user_id)
    await NotificationService(session).create(
        user_id=user_id,
        type=NotificationType.CONNECTION_REQUESTED,
        payload={
            "connection_id": connection.id,
            "from_user_id": current_user.id,
            "from_user_name": current_user.name,
        },
    )
    return await _to_response(session, connection)


@router.post(
    "/connections/{connection_id}/accept",
    response_model=ConnectionResponse,
    summary="연결 요청 수락",
)
async def accept_connection(
    connection_id: str,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> ConnectionResponse:
    svc = ConnectionService(session)
    connection = await svc.accept(connection_id, current_user.id)
    # 요청자에게 수락 알림
    await NotificationService(session).create(
        user_id=connection.follower_id,
        type=NotificationType.CONNECTION_ACCEPTED,
        payload={
            "connection_id": connection.id,
            "accepted_by_user_id": current_user.id,
            "accepted_by_user_name": current_user.name,
        },
    )
    return await _to_response(session, connection)


@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="연결 제거/요청 취소",
)
async def remove_connection(
    connection_id: str,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> None:
    svc = ConnectionService(session)
    await svc.remove(connection_id, current_user.id)


@router.get(
    "/users/{user_id}/connections",
    response_model=list[ConnectionResponse],
    summary="사용자의 연결 목록",
)
async def list_connections(
    user_id: str,
    session: AsyncSessionDep,
    direction: str = Query(
        "followers",
        pattern="^(followers|following)$",
        description="followers=나를 팔로우, following=내가 팔로우",
    ),
    status_: ConnectionStatus | None = Query(
        None, alias="status", description="상태 필터"
    ),
) -> list[ConnectionResponse]:
    svc = ConnectionService(session)
    rows = (
        await svc.list_followers(user_id, status=status_)
        if direction == "followers"
        else await svc.list_following(user_id, status=status_)
    )
    out: list[ConnectionResponse] = []
    for c in rows:
        out.append(await _to_response(session, c))
    return out


@router.get(
    "/users/{user_id}/connections/count",
    summary="사용자의 ACCEPTED 연결 수",
)
async def count_connections(
    user_id: str,
    session: AsyncSessionDep,
) -> dict[str, int]:
    svc = ConnectionService(session)
    n = await svc.count(user_id)
    return {"user_id_hash": user_id[:8], "count": n}
