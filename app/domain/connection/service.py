"""Connection domain service."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.domain.connection.enums import ConnectionStatus
from app.domain.connection.models import Connection
from app.domain.connection.repository import ConnectionRepository
from app.domain.user.service import UserService


class ConnectionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ConnectionRepository(session)

    async def request(self, follower_id: str, following_id: str) -> Connection:
        if follower_id == following_id:
            raise BadRequestError(detail="본인에게는 연결 요청을 보낼 수 없습니다.")

        user_service = UserService(self.session)
        await user_service.get_by_id(following_id)

        existing = await self.repository.get_pair(follower_id, following_id)
        if existing is not None:
            raise ConflictError(detail="이미 연결 요청이 존재합니다.")

        connection = Connection(
            follower_id=follower_id,
            following_id=following_id,
            status=ConnectionStatus.PENDING,
        )
        return await self.repository.create(connection)

    async def accept(self, connection_id: str, acceptor_user_id: str) -> Connection:
        connection = await self.repository.get_by_id(connection_id)
        if connection is None:
            raise NotFoundError(detail="연결 요청을 찾을 수 없습니다.")
        if connection.following_id != acceptor_user_id:
            raise ForbiddenError(detail="본인에게 온 연결 요청만 수락할 수 있습니다.")
        if connection.status is ConnectionStatus.ACCEPTED:
            return connection  # 멱등

        connection.status = ConnectionStatus.ACCEPTED
        connection.accepted_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(connection)
        return connection

    async def remove(self, connection_id: str, requester_id: str) -> None:
        connection = await self.repository.get_by_id(connection_id)
        if connection is None:
            raise NotFoundError(detail="연결 요청을 찾을 수 없습니다.")
        if requester_id not in (connection.follower_id, connection.following_id):
            raise ForbiddenError(detail="관련된 사용자만 삭제할 수 있습니다.")
        await self.repository.delete(connection)

    async def list_followers(
        self, user_id: str, *, status: ConnectionStatus | None = None
    ) -> list[Connection]:
        await UserService(self.session).get_by_id(user_id)
        return await self.repository.list_followers(user_id, status=status)

    async def list_following(
        self, user_id: str, *, status: ConnectionStatus | None = None
    ) -> list[Connection]:
        await UserService(self.session).get_by_id(user_id)
        return await self.repository.list_following(user_id, status=status)

    async def count(self, user_id: str) -> int:
        return await self.repository.count_connections(user_id)
