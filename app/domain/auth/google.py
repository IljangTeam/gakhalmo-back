"""Google OAuth2 HTTP 클라이언트.

인가 URL 생성 + 토큰 교환 + userinfo 조회 세 가지 책임만 담당.
외부 네트워크 실패는 `BadRequestError`로 래핑해 API 경계에서 관리 가능하게 한다.
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.config.settings import Settings, get_settings
from app.core.exceptions import BadRequestError
from app.domain.auth.google_constants import (
    GOOGLE_AUTHORIZE_URL,
    GOOGLE_OAUTH_SCOPE,
    GOOGLE_TOKEN_URL,
    GOOGLE_USERINFO_URL,
)

_HTTP_TIMEOUT_SECONDS = 10.0


class GoogleOAuthClient:
    """Google OAuth 엔드포인트 래퍼."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    # ========== URL ==========

    def build_authorize_url(self, state: str) -> str:
        """Google 인가 URL 생성 (프론트 리디렉션용)."""
        params = {
            "client_id": self._settings.GOOGLE_CLIENT_ID,
            "redirect_uri": self._settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": GOOGLE_OAUTH_SCOPE,
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"

    # ========== Token Exchange ==========

    async def exchange_code_for_token(self, code: str) -> dict:
        """authorization code → access_token 교환."""
        payload = {
            "code": code,
            "client_id": self._settings.GOOGLE_CLIENT_ID,
            "client_secret": self._settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": self._settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(
                    GOOGLE_TOKEN_URL,
                    data=payload,
                    headers={"Accept": "application/json"},
                )
            except httpx.HTTPError as exc:
                raise BadRequestError(
                    detail=f"Google 토큰 교환 실패: {exc}"
                ) from exc

        if response.status_code != httpx.codes.OK:
            raise BadRequestError(
                detail=f"Google 토큰 교환 실패 (status={response.status_code})"
            )
        return response.json()

    # ========== UserInfo ==========

    async def fetch_userinfo(self, access_token: str) -> dict:
        """Google access_token으로 사용자 프로필 조회."""
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            try:
                response = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.HTTPError as exc:
                raise BadRequestError(
                    detail=f"Google 프로필 조회 실패: {exc}"
                ) from exc

        if response.status_code != httpx.codes.OK:
            raise BadRequestError(
                detail=f"Google 프로필 조회 실패 (status={response.status_code})"
            )
        return response.json()
