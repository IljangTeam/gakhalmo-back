from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.user.models import User
from app.domain.user.schemas import UserUpdate
from app.domain.user.service import UserService


@dataclass
class UpdateUserUseCase:
    """사용자 정보 수정 유스케이스.

    처리 흐름:
    1. 기존 사용자 조회
    2. 변경된 필드 적용
    3. 변경 사항 영속화
    """

    session: AsyncSession

    async def execute(self, user_id: str, data: UserUpdate) -> User:
        """유스케이스 실행."""
        service = UserService(self.session)

        # 기존 사용자 조회 (없으면 NotFoundError 발생)
        user = await service.get_by_id(user_id)

        update_data = data.model_dump(exclude_unset=True)

        # 변경된 필드 적용
        for field, value in update_data.items():
            setattr(user, field, value)

        # 서비스를 통해 영속화
        return await service.update(user)
    

# depends 정의
def get_update_user_use_case(session: AsyncSessionDep) -> UpdateUserUseCase:
    """UpdateUserUseCase 의존성 주입 함수."""
    return UpdateUserUseCase(session=session)


# Annotated 정의
UpdateUserUseCaseDep = Annotated[UpdateUserUseCase, Depends(get_update_user_use_case)]