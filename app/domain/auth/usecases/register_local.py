"""로컬 회원가입 유스케이스."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.domain.auth.dependencies import AuthServiceDep
from app.domain.auth.schemas import RegisterRequest
from app.domain.auth.service import AuthService
from app.domain.user.models import User


@dataclass
class RegisterLocalUseCase:
    """로컬 회원가입 — User + AuthIdentity(LOCAL) 생성."""

    auth_service: AuthService

    async def execute(self, data: RegisterRequest) -> User:
        return await self.auth_service.register_local(
            email=data.email,
            password=data.password,
            name=data.name,
        )


def register_local_use_case(auth_service: AuthServiceDep) -> RegisterLocalUseCase:
    return RegisterLocalUseCase(auth_service=auth_service)


RegisterLocalUseCaseDep = Annotated[
    RegisterLocalUseCase, Depends(register_local_use_case)
]
