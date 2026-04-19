"""보안 원시 유틸 - 비밀번호 해시 + JWT + OAuth state 서명.

도메인 의존성 없음. auth 도메인이 이 모듈을 소비한다.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config.settings import get_settings

_settings = get_settings()


# ========== Password ==========

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=_settings.BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ========== JWT ==========

class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"
    OAUTH_STATE = "oauth_state"


def _create_token(subject: str, *, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, _settings.JWT_SECRET, algorithm=_settings.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=_settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=_settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, *, expected_type: str | None = None) -> dict[str, Any]:
    """JWT 디코드. 만료/서명/타입 검증. 실패 시 jwt 예외 그대로 raise."""
    payload = jwt.decode(
        token,
        _settings.JWT_SECRET,
        algorithms=[_settings.JWT_ALGORITHM],
    )
    if expected_type is not None and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"Expected token type {expected_type!r}, got {payload.get('type')!r}"
        )
    return payload


# ========== OAuth state (CSRF) ==========

def create_oauth_state(*, nonce: str | None = None) -> str:
    """CSRF 방지용 서명 state. 서버 세션 없이 라운드트립 검증 가능."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "type": TokenType.OAUTH_STATE,
        "nonce": nonce or secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(seconds=_settings.OAUTH_STATE_TTL_SECONDS),
    }
    return jwt.encode(
        payload, _settings.JWT_SECRET, algorithm=_settings.JWT_ALGORITHM
    )


def verify_oauth_state(state: str) -> None:
    """state 서명/만료/type 검증. 실패 시 jwt.InvalidTokenError."""
    decode_token(state, expected_type=TokenType.OAUTH_STATE)
