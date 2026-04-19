"""Alembic environment — async SQLAlchemy with project settings."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config.settings import get_settings
from app.core.database import Base

# 모델 임포트 — Base.metadata에 모든 테이블이 등록되도록 강제
from app.domain.auth import models as _auth_models  # noqa: F401
from app.domain.meeting import models as _meeting_models  # noqa: F401
from app.domain.regions import models as _regions_models  # noqa: F401
from app.domain.user import models as _user_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_settings = get_settings()
# configparser (BasicInterpolation) 가 % 를 해석하므로 URL-encoded 문자(`%21` 등)는 이스케이프.
config.set_main_option("sqlalchemy.url", _settings.DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """URL만 사용한 오프라인 마이그레이션."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """비동기 엔진 기반 온라인 마이그레이션."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
