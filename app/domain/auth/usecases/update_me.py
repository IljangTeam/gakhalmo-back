"""본인 프로필 수정 유스케이스."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AsyncSessionDep
from app.domain.auth.schemas import UpdateMeRequest
from app.domain.user.models import User
from app.domain.user.service import UserService


@dataclass
class UpdateMeUseCase:
    """로그인 사용자가 본인 프로필을 수정.

    `exclude_unset=True` 로 클라이언트가 보낸 필드만 반영한다.
    태그는 빈 리스트 `[]` 가 '전체 제거' 의미를 갖도록 None vs [] 를 구분한다.
    """

    session: AsyncSession

    async def execute(self, user: User, data: UpdateMeRequest) -> User:
        service = UserService(self.session)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(user, field, value)
        return await service.update(user)


def update_me_use_case(session: AsyncSessionDep) -> UpdateMeUseCase:
    return UpdateMeUseCase(session=session)


UpdateMeUseCaseDep = Annotated[UpdateMeUseCase, Depends(update_me_use_case)]
