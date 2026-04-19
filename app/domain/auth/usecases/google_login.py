"""Google 로그인 시작 — 서명된 state + 인가 URL 생성."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.core.security import create_oauth_state
from app.domain.auth.dependencies import AuthServiceDep
from app.domain.auth.service import AuthService


@dataclass
class GoogleLoginUseCase:
    """Google 인가 URL 빌드.

    state는 JWT(HS256)로 서명되어 서버 세션 저장 없이도 callback에서
    서명/만료를 검증할 수 있다. TTL은 Settings.OAUTH_STATE_TTL_SECONDS.
    """

    auth_service: AuthService

    def execute(self) -> tuple[str, str]:
        """(authorize_url, state) 반환."""
        state = create_oauth_state()
        url = self.auth_service.google_client.build_authorize_url(state)
        return url, state


def google_login_use_case(auth_service: AuthServiceDep) -> GoogleLoginUseCase:
    return GoogleLoginUseCase(auth_service=auth_service)


GoogleLoginUseCaseDep = Annotated[GoogleLoginUseCase, Depends(google_login_use_case)]
