"""Auth API 라우터 — 로컬 회원가입/로그인, Google OAuth, JWT refresh, /me."""

from __future__ import annotations

from fastapi import APIRouter, Query, status
from fastapi.responses import RedirectResponse

from app.domain.auth.dependencies import CurrentUserDep
from app.domain.auth.schemas import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.domain.auth.usecases import (
    GetMeUseCaseDep,
    GoogleCallbackUseCaseDep,
    GoogleLoginUseCaseDep,
    LoginLocalUseCaseDep,
    RefreshTokenUseCaseDep,
    RegisterLocalUseCaseDep,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=MeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="로컬 회원가입",
)
async def register_local(
    data: RegisterRequest,
    use_case: RegisterLocalUseCaseDep,
) -> MeResponse:
    user = await use_case.execute(data)
    return MeResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="로컬 로그인 (토큰 발급)",
)
async def login_local(
    data: LoginRequest,
    use_case: LoginLocalUseCaseDep,
) -> TokenResponse:
    return await use_case.execute(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="refresh 토큰으로 access 토큰 재발급",
)
async def refresh_token(
    data: RefreshRequest,
    use_case: RefreshTokenUseCaseDep,
) -> TokenResponse:
    return await use_case.execute(data)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="현재 인증된 사용자 정보",
)
async def get_me(
    current_user: CurrentUserDep,
    use_case: GetMeUseCaseDep,
) -> MeResponse:
    user = use_case.execute(current_user)
    return MeResponse.model_validate(user)


@router.get(
    "/google/login",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Google OAuth 인가 페이지로 리디렉션",
)
async def google_login(
    use_case: GoogleLoginUseCaseDep,
) -> RedirectResponse:
    url, _state = use_case.execute()
    return RedirectResponse(
        url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@router.get(
    "/google/callback",
    response_model=TokenResponse,
    summary="Google OAuth 콜백 — state/code 검증 → JWT 발급",
)
async def google_callback(
    use_case: GoogleCallbackUseCaseDep,
    code: str = Query(..., description="Google이 발급한 authorization code"),
    state: str = Query(..., description="서명된 CSRF 방지 state (필수)"),
) -> TokenResponse:
    return await use_case.execute(code, state)
