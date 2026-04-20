"""Connection repository."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.connection.enums import ConnectionStatus
from app.domain.connection.models import Connection


class ConnectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, connection: Connection) -> Connection:
        self.session.add(connection)
        await self.session.commit()
        await self.session.refresh(connection)
        return connection

    async def get_pair(
        self, follower_id: str, following_id: str
    ) -> Connection | None:
        result = await self.session.execute(
            select(Connection).where(
                Connection.follower_id == follower_id,
                Connection.following_id == following_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, connection_id: str) -> Connection | None:
        result = await self.session.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def list_followers(
        self, user_id: str, *, status: ConnectionStatus | None = None
    ) -> list[Connection]:
        stmt = select(Connection).where(Connection.following_id == user_id)
        if status is not None:
            stmt = stmt.where(Connection.status == status)
        stmt = stmt.order_by(Connection.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_following(
        self, user_id: str, *, status: ConnectionStatus | None = None
    ) -> list[Connection]:
        stmt = select(Connection).where(Connection.follower_id == user_id)
        if status is not None:
            stmt = stmt.where(Connection.status == status)
        stmt = stmt.order_by(Connection.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_connections(self, user_id: str) -> int:
        """양방향 포함, ACCEPTED 만 카운트."""
        result = await self.session.execute(
            select(func.count(Connection.id)).where(
                or_(
                    Connection.follower_id == user_id,
                    Connection.following_id == user_id,
                ),
                Connection.status == ConnectionStatus.ACCEPTED,
            )
        )
        return int(result.scalar_one() or 0)

    async def delete(self, connection: Connection) -> None:
        await self.session.delete(connection)
        await self.session.commit()
