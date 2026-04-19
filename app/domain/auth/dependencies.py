"""Auth 도메인 FastAPI 의존성.

- `CurrentUserDep`: Authorization 헤더의 Bearer access_token을 검증하고 User를 주입.
- `get_auth_service`: AuthService 팩토리 (세션 주입).
"""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.dependencies import AsyncSessionDep
from app.core.exceptions import UnauthorizedError
from app.core.security import TokenType, decode_token
from app.domain.auth.service import AuthService
from app.domain.user.models import User
from app.domain.user.repository import UserRepository

# auto_error=False — 401 응답 포맷을 UnauthorizedError로 통일하기 위해.
_bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAccess")


def get_auth_service(session: AsyncSessionDep) -> AuthService:
    """AuthService 팩토리 — 라우터/유스케이스에서 DI용."""
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def _get_current_user(
    session: AsyncSessionDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ] = None,
) -> User:
    """Bearer access_token → User 해석. 실패 시 UnauthorizedError."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError(detail="인증 토큰이 필요합니다.")

    try:
        payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError(detail="유효하지 않은 access 토큰입니다.") from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise UnauthorizedError(detail="유효하지 않은 access 토큰입니다.")

    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError(detail="사용자를 찾을 수 없습니다.")
    if not user.is_active:
        raise UnauthorizedError(detail="비활성화된 계정입니다.")
    return user


CurrentUserDep = Annotated[User, Depends(_get_current_user)]
