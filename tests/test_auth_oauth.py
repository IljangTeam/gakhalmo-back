"""OAuth state (CSRF) — signed JWT roundtrip, expiration, tampering."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config.settings import get_settings
from app.core.security import (
    TokenType,
    create_oauth_state,
    verify_oauth_state,
)


def test_oauth_state_roundtrip_ok() -> None:
    state = create_oauth_state()
    # Must not raise.
    verify_oauth_state(state)


def test_oauth_state_embeds_type_and_nonce() -> None:
    state = create_oauth_state(nonce="fixed-nonce")
    settings = get_settings()
    payload = jwt.decode(
        state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["type"] == TokenType.OAUTH_STATE
    assert payload["nonce"] == "fixed-nonce"


def test_oauth_state_tampered_rejected() -> None:
    state = create_oauth_state()
    # Flip a few characters of the signature segment.
    header, body, sig = state.split(".")
    tampered = f"{header}.{body}.{sig[:-4]}AAAA"
    with pytest.raises(jwt.InvalidTokenError):
        verify_oauth_state(tampered)


def test_oauth_state_expired_rejected() -> None:
    settings = get_settings()
    past = datetime.now(UTC) - timedelta(seconds=10)
    payload = {
        "type": TokenType.OAUTH_STATE,
        "nonce": "x",
        "iat": past - timedelta(seconds=30),
        "exp": past,
    }
    expired = jwt.encode(
        payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_oauth_state(expired)


def test_oauth_state_wrong_type_rejected() -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": "user-1",
        "type": TokenType.ACCESS,
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    wrong_type = jwt.encode(
        payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(jwt.InvalidTokenError):
        verify_oauth_state(wrong_type)
