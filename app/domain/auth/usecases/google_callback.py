"""Google OAuth 콜백 처리 유스케이스."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends

from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import verify_oauth_state
from app.domain.auth.dependencies import AuthServiceDep
from app.domain.auth.schemas import TokenResponse
from app.domain.auth.service import AuthService


@dataclass
class GoogleCallbackUseCase:
    """authorization code → 토큰 교환 → 프로필 조회 → User upsert → JWT 발급."""

    auth_service: AuthService

    async def execute(self, code: str, state: str) -> TokenResponse:
        try:
            verify_oauth_state(state)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError(
                detail="유효하지 않거나 만료된 OAuth state 입니다."
            ) from exc

        token_payload = await self.auth_service.google_client.exchange_code_for_token(
            code
        )
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise BadRequestError(detail="Google access_token이 응답에 없습니다.")

        userinfo = await self.auth_service.google_client.fetch_userinfo(access_token)

        google_sub = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name") or email
        profile_image = userinfo.get("picture")

        if not isinstance(google_sub, str) or not google_sub:
            raise BadRequestError(detail="Google 응답에 sub이 없습니다.")
        if not isinstance(email, str) or not email:
            raise BadRequestError(detail="Google 응답에 email이 없습니다.")
        if not isinstance(name, str) or not name:
            name = email

        user = await self.auth_service.find_or_create_from_google(
            google_sub=google_sub,
            email=email,
            name=name,
            profile_image=profile_image if isinstance(profile_image, str) else None,
        )
        return self.auth_service.issue_tokens(user)


def google_callback_use_case(auth_service: AuthServiceDep) -> GoogleCallbackUseCase:
    return GoogleCallbackUseCase(auth_service=auth_service)


GoogleCallbackUseCaseDep = Annotated[
    GoogleCallbackUseCase, Depends(google_callback_use_case)
]
