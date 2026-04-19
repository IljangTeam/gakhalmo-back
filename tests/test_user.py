"""User repository — password_hash=None + soft delete filter."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.models import User
from app.domain.user.repository import UserRepository


async def test_create_without_password_and_read_by_email(
    db_session: AsyncSession,
) -> None:
    repo = UserRepository(db_session)
    user = User(email="oauth-only@example.com", name="OAuth", password_hash=None)
    await repo.create(user)

    fetched = await repo.get_by_email("oauth-only@example.com")
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.password_hash is None


async def test_soft_delete_filters_out_user(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = User(email="soft@example.com", name="Soft", password_hash=None)
    await repo.create(user)

    assert await repo.get_by_id(user.id) is not None

    await repo.soft_delete(user)
    assert user.deleted_at is not None

    assert await repo.get_by_id(user.id) is None
    assert await repo.get_by_email("soft@example.com") is None
