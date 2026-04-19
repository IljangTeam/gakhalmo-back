"""Refresh 토큰 갱신 유스케이스."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.domain.auth.dependencies import AuthServiceDep
from app.domain.auth.schemas import RefreshRequest, TokenResponse
from app.domain.auth.service import AuthService


@dataclass
class RefreshTokenUseCase:
    """refresh_token 검증 + 새 토큰 쌍 발급."""

    auth_service: AuthService

    async def execute(self, data: RefreshRequest) -> TokenResponse:
        return await self.auth_service.refresh(data.refresh_token)


def refresh_token_use_case(auth_service: AuthServiceDep) -> RefreshTokenUseCase:
    return RefreshTokenUseCase(auth_service=auth_service)


RefreshTokenUseCaseDep = Annotated[RefreshTokenUseCase, Depends(refresh_token_use_case)]
