"""AuthIdentity repository.

트랜잭션 정책:
- `create`는 `flush`만 수행 — 커밋은 호출 측(`AuthService`)이 책임.
  (User 신규 생성과 AuthIdentity 생성을 한 트랜잭션으로 묶어야 하기 때문.)
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.auth.enums import AuthProvider
from app.domain.auth.models import AuthIdentity


class AuthIdentityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_provider(
        self,
        provider: AuthProvider,
        provider_user_id: str,
    ) -> AuthIdentity | None:
        result = await self.session.execute(
            select(AuthIdentity).where(
                AuthIdentity.provider == provider,
                AuthIdentity.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[AuthIdentity]:
        result = await self.session.execute(
            select(AuthIdentity).where(AuthIdentity.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create(self, identity: AuthIdentity) -> AuthIdentity:
        """AuthIdentity 추가 (flush만 수행 — 커밋은 service 트랜잭션이 책임)."""
        self.session.add(identity)
        await self.session.flush()
        await self.session.refresh(identity)
        return identity
