"""로컬 로그인 유스케이스."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.domain.auth.dependencies import AuthServiceDep
from app.domain.auth.schemas import LoginRequest, TokenResponse
from app.domain.auth.service import AuthService


@dataclass
class LoginLocalUseCase:
    """이메일/비밀번호 검증 + 토큰 발급."""

    auth_service: AuthService

    async def execute(self, data: LoginRequest) -> TokenResponse:
        user = await self.auth_service.authenticate_local(
            email=data.email,
            password=data.password,
        )
        return self.auth_service.issue_tokens(user)


def login_local_use_case(auth_service: AuthServiceDep) -> LoginLocalUseCase:
    return LoginLocalUseCase(auth_service=auth_service)


LoginLocalUseCaseDep = Annotated[LoginLocalUseCase, Depends(login_local_use_case)]
