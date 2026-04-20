"""Auth Pydantic 스키마 — 요청/응답 DTO."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """로컬 회원가입 요청."""

    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., min_length=8, max_length=128, description="비밀번호 (8자 이상)")
    name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")


class LoginRequest(BaseModel):
    """로컬 로그인 요청."""

    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., min_length=1, description="비밀번호")


class TokenResponse(BaseModel):
    """토큰 발급 응답."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="access_token 유효기간(초)")


class RefreshRequest(BaseModel):
    """리프레시 토큰 교환 요청."""

    refresh_token: str = Field(..., min_length=1)


class GoogleCallbackQuery(BaseModel):
    """Google OAuth 콜백 쿼리 파라미터."""

    code: str = Field(..., description="Google이 발급한 authorization code")
    state: str | None = Field(None, description="CSRF 방지용 state")


class UpdateMeRequest(BaseModel):
    """본인 프로필 수정 요청."""

    name: str | None = Field(None, min_length=1, max_length=100)
    profile_image: str | None = None
    bio: str | None = Field(None, max_length=500)
    job: str | None = Field(None, max_length=100)
    tags: list[str] | None = Field(
        None,
        description="관심 태그 배열. None 이면 미변경, [] 이면 전체 제거",
    )
    notification_prefs: dict | None = Field(
        None,
        description="알림 설정 key→bool 맵. None=미변경, {}=전체 초기화",
    )


class MeResponse(BaseModel):
    """현재 인증된 사용자 정보."""

    id: str
    email: EmailStr
    name: str
    profile_image: str | None = None
    bio: str | None = None
    job: str | None = None
    tags: list[str] | None = None
    notification_prefs: dict | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
