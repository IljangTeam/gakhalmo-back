from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.user.models import User
from app.domain.user.service import UserService


@dataclass
class GetUserUseCase:
    """ID로 사용자 조회 유스케이스.

    처리 흐름:
    1. 서비스를 통해 사용자 조회 (없으면 NotFoundError 발생)
    """

    session: AsyncSession

    async def execute(self, user_id: str) -> User:
        """유스케이스 실행."""
        service = UserService(self.session)
        return await service.get_by_id(user_id)


@dataclass
class GetUserByEmailUseCase:
    """이메일로 사용자 조회 유스케이스.

    처리 흐름:
    1. 이메일로 사용자 조회 (없으면 None 반환)
    """

    session: AsyncSession

    async def execute(self, email: str) -> User | None:
        """유스케이스 실행."""
        service = UserService(self.session)
        return await service.get_by_email(email)

def get_user_use_case(session: AsyncSessionDep) -> GetUserUseCase:
    return GetUserUseCase(session=session)

def get_user_by_email_use_case(session: AsyncSessionDep) -> GetUserByEmailUseCase:
    return GetUserByEmailUseCase(session=session)

GetUserUseCaseDep = Annotated[GetUserUseCase, Depends(get_user_use_case)]
GetUserByEmailUseCaseDep = Annotated[GetUserByEmailUseCase, Depends(get_user_by_email_use_case)]