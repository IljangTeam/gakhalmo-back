"""Pytest fixtures: async sqlite engine, session, httpx AsyncClient.

- Uses aiosqlite in-memory with StaticPool so every session shares the same DB.
- Builds schema from SQLAlchemy metadata (no Alembic, no seed JSON).
- Overrides `app.core.database.get_async_session` so the FastAPI app speaks to
  the sqlite test engine instead of the real Postgres engine.
- Skips FastAPI lifespan (default ASGITransport behavior) so the production
  `init_db` / `seed_regions` never runs against the test DB.
"""

from __future__ import annotations

import logging
import os

# Lock in permissive Settings + required secrets before the app imports.
# Must run before any `from app...` import so `get_settings()` sees ENV=test
# (skips dev/prod invariant checks) and finds every required field.
os.environ.setdefault("ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "mysql+asyncmy://test:test@localhost:3306/test",
)
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 32)
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_async_session  # noqa: E402
from app.domain.regions import models as _regions_models  # noqa: F401,E402 — register tables
from app.domain.user import models as _user_models  # noqa: F401,E402 — register tables
from app.domain.meeting import models as _meeting_models  # noqa: F401,E402 — register tables
from app.domain.notification import models as _notification_models  # noqa: F401,E402
from app.domain.review import models as _review_models  # noqa: F401,E402
from app.domain.connection import models as _connection_models  # noqa: F401,E402
from app.domain.chat import models as _chat_models  # noqa: F401,E402
from app.main import app  # noqa: E402

logger = logging.getLogger(__name__)

# Register auth models if Stream A has landed them; if the module is missing or
# incomplete, auth-dependent tests skip but the rest of the suite still runs.
AUTH_MODELS_AVAILABLE = True
try:
    from app.domain.auth import models as _auth_models  # noqa: F401,E402
except ImportError as exc:  # pragma: no cover — depends on Stream A progress
    AUTH_MODELS_AVAILABLE = False
    logger.warning("app.domain.auth.models not importable yet: %s", exc)


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Session-scoped aiosqlite engine with shared in-memory DB."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Function-scoped session bound to the test engine."""
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient wrapping the FastAPI app with overridden DB dep."""
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def _override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override_get_async_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.fixture
def auth_models_available() -> bool:
    """Expose the auth-import flag to tests that want to skip."""
    return AUTH_MODELS_AVAILABLE
