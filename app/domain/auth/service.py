"""Auth 도메인 서비스 — User 생성/조회 + AuthIdentity + JWT 발급의 오케스트레이션.

트랜잭션 경계:
- `register_local` / `find_or_create_from_google`는 User + AuthIdentity 동시 생성이
  필요하므로 서비스 계층에서 직접 `commit`/`rollback`을 수행한다.
- `authenticate_local`은 last_login_at 갱신 한 건만 있으므로 단일 `commit`.
- `issue_tokens` / `refresh`는 순수 유틸 — DB 변경 없음.
"""

from __future__ import annotations

from datetime import UTC, datetime

import jwt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.auth.enums import AuthProvider
from app.domain.auth.google import GoogleOAuthClient
from app.domain.auth.models import AuthIdentity
from app.domain.auth.repository import AuthIdentityRepository
from app.domain.auth.schemas import TokenResponse
from app.domain.user.models import User
from app.domain.user.repository import UserRepository

_settings = get_settings()


class AuthService:
    """인증 흐름 오케스트레이션."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        google_client: GoogleOAuthClient | None = None,
    ):
        self.session = session
        self.user_repository = UserRepository(session)
        self.identity_repository = AuthIdentityRepository(session)
        self.google_client = google_client or GoogleOAuthClient()

    # ========== 로컬 회원가입/로그인 ==========

    async def register_local(self, email: str, password: str, name: str) -> User:
        """로컬 회원가입 — User + AuthIdentity(LOCAL)를 한 트랜잭션에서 생성."""
        existing = await self.user_repository.get_by_email(email)
        if existing is not None:
            raise ConflictError(detail="이미 등록된 이메일입니다.")

        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
        )

        try:
            self.session.add(user)
            await self.session.flush()
            await self.session.refresh(user)

            identity = AuthIdentity(
                user_id=user.id,
                provider=AuthProvider.LOCAL,
                provider_user_id=email,
                email=email,
            )
            await self.identity_repository.create(identity)

            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            raise

        await self.session.refresh(user)
        return user

    async def authenticate_local(self, email: str, password: str) -> User:
        """이메일/비밀번호 검증 + last_login_at 갱신."""
        user = await self.user_repository.get_by_email(email)
        if user is None or user.password_hash is None:
            # 사용자 유무를 노출하지 않기 위해 동일 메시지.
            raise UnauthorizedError(detail="이메일 또는 비밀번호가 올바르지 않습니다.")
        if not user.is_active:
            raise UnauthorizedError(detail="비활성화된 계정입니다.")
        if not verify_password(password, user.password_hash):
            raise UnauthorizedError(detail="이메일 또는 비밀번호가 올바르지 않습니다.")

        user.last_login_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    # ========== Google OAuth ==========

    async def find_or_create_from_google(
        self,
        google_sub: str,
        email: str,
        name: str,
        profile_image: str | None,
    ) -> User:
        """Google 프로필 → User 매핑 (필요 시 신규 생성 또는 기존 User에 ID 연결)."""
        existing_identity = await self.identity_repository.get_by_provider(
            AuthProvider.GOOGLE, google_sub
        )
        if existing_identity is not None:
            user = await self.user_repository.get_by_id(existing_identity.user_id)
            if user is None:
                # identity는 있지만 user가 소프트 삭제된 비정상 상태 → 재로그인 차단.
                raise UnauthorizedError(detail="연결된 사용자 계정이 존재하지 않습니다.")
            user.last_login_at = datetime.now(UTC)
            await self.session.commit()
            await self.session.refresh(user)
            return user

        try:
            user = await self.user_repository.get_by_email(email)
            if user is None:
                # 신규 유저 — OAuth-only 계정이므로 password_hash는 NULL 유지.
                user = User(
                    email=email,
                    name=name,
                    profile_image=profile_image,
                    last_login_at=datetime.now(UTC),
                )
                self.session.add(user)
                await self.session.flush()
                await self.session.refresh(user)
            elif _settings.AUTH_ALLOW_GOOGLE_AUTOLINK:
                # 정책적으로 허용된 경우에만 같은 이메일 로컬 계정에 자동 연결.
                user.last_login_at = datetime.now(UTC)
            else:
                # 기본 정책: 자동 연결 금지. 사용자에게 로컬 로그인 후
                # 명시적 연결 플로우를 타도록 유도.
                await self.session.rollback()
                raise ConflictError(
                    detail=(
                        "동일 이메일의 로컬 계정이 존재합니다. "
                        "로컬로 로그인한 뒤 Google 계정을 연결해 주세요."
                    )
                )

            identity = AuthIdentity(
                user_id=user.id,
                provider=AuthProvider.GOOGLE,
                provider_user_id=google_sub,
                email=email,
            )
            await self.identity_repository.create(identity)

            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            raise

        await self.session.refresh(user)
        return user

    # ========== JWT ==========

    def issue_tokens(self, user: User) -> TokenResponse:
        """access + refresh 토큰 발급."""
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            token_type="bearer",
            expires_in=_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """refresh_token 검증 후 새 토큰 쌍 발급."""
        try:
            payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError(detail="유효하지 않은 refresh 토큰입니다.") from exc

        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise UnauthorizedError(detail="유효하지 않은 refresh 토큰입니다.")

        user = await self.user_repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(detail="사용자를 찾을 수 없거나 비활성 상태입니다.")

        return self.issue_tokens(user)
