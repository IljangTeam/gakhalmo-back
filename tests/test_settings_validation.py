"""Settings model validator — required secrets + dev/prod invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import Settings

_STRONG_SECRET = "x" * 64
_PROD_DB = "postgresql+asyncpg://u:p@db.internal:5432/gakhalmo"


def _base_secrets(**overrides: object) -> dict[str, object]:
    """지정되지 않으면 시크릿 슬롯을 채워주는 헬퍼 (env 누락 검증 제외)."""
    base: dict[str, object] = {
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/x",
        "JWT_SECRET": _STRONG_SECRET,
        "GOOGLE_CLIENT_ID": "gid",
        "GOOGLE_CLIENT_SECRET": "gsec",
    }
    base.update(overrides)
    return base


def _prod_defaults(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = _base_secrets(
        ENV="prod",
        DATABASE_URL=_PROD_DB,
        DEBUG=False,
        GOOGLE_REDIRECT_URI="https://app.example.com/cb",
        RUN_STARTUP_SEED=False,
    )
    base.update(overrides)
    return base


# ─── 필수 시크릿 누락 시 즉시 fail ───────────────────────────────────


def test_missing_jwt_secret_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError) as ei:
        Settings(
            _env_file=None,  # ignore project .env
            DATABASE_URL="postgresql+asyncpg://u:p@h:5432/x",
            GOOGLE_CLIENT_ID="gid",
            GOOGLE_CLIENT_SECRET="gsec",
        )
    assert "JWT_SECRET" in str(ei.value)


def test_short_jwt_secret_fails() -> None:
    with pytest.raises(ValidationError) as ei:
        Settings(**_base_secrets(JWT_SECRET="too-short"))
    assert "JWT_SECRET" in str(ei.value)


def test_missing_database_url_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError) as ei:
        Settings(
            _env_file=None,
            JWT_SECRET=_STRONG_SECRET,
            GOOGLE_CLIENT_ID="gid",
            GOOGLE_CLIENT_SECRET="gsec",
        )
    assert "DATABASE_URL" in str(ei.value)


def test_missing_google_creds_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    with pytest.raises(ValidationError) as ei:
        Settings(
            _env_file=None,
            DATABASE_URL="postgresql+asyncpg://u:p@h:5432/x",
            JWT_SECRET=_STRONG_SECRET,
        )
    assert "GOOGLE_CLIENT_ID" in str(ei.value) or "GOOGLE_CLIENT_SECRET" in str(
        ei.value
    )


# ─── Prod invariants ────────────────────────────────────────────────


def test_prod_happy_path_accepts() -> None:
    s = Settings(**_prod_defaults())
    assert s.is_production is True


def test_prod_rejects_debug_on() -> None:
    with pytest.raises(ValidationError) as ei:
        Settings(**_prod_defaults(DEBUG=True))
    assert "DEBUG" in str(ei.value)


def test_prod_rejects_localhost_db() -> None:
    with pytest.raises(ValidationError) as ei:
        Settings(
            **_prod_defaults(
                DATABASE_URL="postgresql+asyncpg://u:p@localhost:5432/x"
            )
        )
    assert "localhost" in str(ei.value)


def test_prod_rejects_http_redirect() -> None:
    with pytest.raises(ValidationError) as ei:
        Settings(
            **_prod_defaults(
                GOOGLE_REDIRECT_URI="http://app.example.com/cb"
            )
        )
    assert "HTTPS" in str(ei.value)


def test_prod_rejects_startup_seed() -> None:
    with pytest.raises(ValidationError) as ei:
        Settings(**_prod_defaults(RUN_STARTUP_SEED=True))
    assert "RUN_STARTUP_SEED" in str(ei.value)


def test_local_is_permissive() -> None:
    # ENV=local은 DEBUG/localhost/http 허용.
    s = Settings(**_base_secrets(ENV="local"))
    assert s.is_production is False


def test_cors_origins_parse_from_csv() -> None:
    s = Settings(
        **_base_secrets(ENV="local", CORS_ORIGINS="https://a.com, https://b.com")
    )
    assert s.CORS_ORIGINS == ["https://a.com", "https://b.com"]
