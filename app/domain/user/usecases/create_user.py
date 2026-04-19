from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.user.models import User
from app.domain.user.schemas import UserCreate
from app.domain.user.service import UserService


@dataclass
class CreateUserUseCase:
    """사용자 생성 유스케이스.

    처리 흐름:
    1. 이메일 중복 검증
    2. User 엔티티 생성
    3. 영속화
    """

    session: AsyncSession

    async def execute(self, data: UserCreate) -> User:
        """유스케이스 실행."""
        service = UserService(self.session)

        # 도메인 규칙 검증 (이메일 중복 체크)
        await service.validate_email_unique(data.email)

        # 엔티티 생성
        user = User(
            name=data.name,
            email=data.email,
            profile_image=data.profile_image,
            bio=data.bio,
        )

        # 서비스를 통해 영속화
        return await service.create(user)

def create_user_use_case(session: AsyncSessionDep) -> CreateUserUseCase:
    return CreateUserUseCase(session=session)

CreateUserUseCaseDep = Annotated[CreateUserUseCase, Depends(create_user_use_case)]