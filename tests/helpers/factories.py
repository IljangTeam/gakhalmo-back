"""Lightweight factories for test fixtures."""

from __future__ import annotations

from ulid import ULID

from app.domain.user.models import User


def new_ulid() -> str:
    return str(ULID())


def make_user(
    *,
    email: str = "test@example.com",
    name: str = "Tester",
    password_hash: str | None = None,
) -> User:
    return User(
        id=new_ulid(),
        email=email,
        name=name,
        password_hash=password_hash,
    )
