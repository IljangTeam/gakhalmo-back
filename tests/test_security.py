"""Security primitives — bcrypt hash/verify + JWT access/refresh typing."""

from __future__ import annotations

import jwt
import pytest

from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_verify_roundtrip() -> None:
    hashed = hash_password("s3cret!")
    assert hashed != "s3cret!"
    assert verify_password("s3cret!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_access_token_roundtrip() -> None:
    token = create_access_token("user-123")
    payload = decode_token(token, expected_type=TokenType.ACCESS)
    assert payload["sub"] == "user-123"
    assert payload["type"] == TokenType.ACCESS


def test_refresh_token_rejected_when_access_expected() -> None:
    refresh = create_refresh_token("user-456")

    # Unchecked decode still succeeds…
    payload = decode_token(refresh)
    assert payload["type"] == TokenType.REFRESH

    # …but asking for ACCESS must raise.
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(refresh, expected_type=TokenType.ACCESS)


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token("user-789")
    payload = decode_token(token, expected_type=TokenType.REFRESH)
    assert payload["sub"] == "user-789"
    assert payload["type"] == TokenType.REFRESH
