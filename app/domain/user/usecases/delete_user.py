from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.user.service import UserService


@dataclass
class DeleteUserUseCase:
    """사용자 삭제 유스케이스.

    처리 흐름:
    1. 사용자 조회 (없으면 NotFoundError 발생)
    2. 서비스를 통해 삭제
    """

    session: AsyncSession

    async def execute(self, user_id: str) -> None:
        """유스케이스 실행."""
        service = UserService(self.session)

        user = await service.get_by_id(user_id)
        await service.delete(user)

def delete_user_use_case(session:AsyncSessionDep) -> DeleteUserUseCase:
    return DeleteUserUseCase(session=session)

DeleteUserUseCaseDep = Annotated[DeleteUserUseCase, Depends(delete_user_use_case)]