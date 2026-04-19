"""현재 사용자 조회 유스케이스."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.domain.user.models import User


@dataclass
class GetMeUseCase:
    """CurrentUserDep으로 주입된 User를 그대로 반환.

    라우터가 Pydantic 응답 스키마로 직렬화한다.
    별도 DB 조회는 없으며, 계층을 일관되게 유지하기 위한 얇은 래퍼.
    """

    def execute(self, user: User) -> User:
        return user


def get_me_use_case() -> GetMeUseCase:
    return GetMeUseCase()


GetMeUseCaseDep = Annotated[GetMeUseCase, Depends(get_me_use_case)]
