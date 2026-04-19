from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.user.models import User
from app.domain.user.service import UserService


@dataclass
class ListUsersUseCase:
    """페이지네이션 기반 사용자 목록 조회."""

    session: AsyncSession

    async def execute(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """유스케이스 실행."""
        service = UserService(self.session)
        return await service.get_all(offset=offset, limit=limit)

def list_users_use_case(session: AsyncSessionDep) -> ListUsersUseCase:
    return ListUsersUseCase(session=session)

ListUsersUseCaseDep = Annotated[ListUsersUseCase, Depends(list_users_use_case)]