"""Application settings loaded from environment variables.

진실의 근원(source of truth) 규칙:
- 필수 시크릿 (JWT_SECRET, DATABASE_URL, GOOGLE_CLIENT_ID/SECRET):
  default 없음. 누락 시 부팅 단계에서 ValidationError.
- 환경별 비시크릿 (CORS_ORIGINS, LOG_LEVEL, REDIRECT_URI 등):
  local/test 편의를 위한 sane default 유지.
- 불변 공개 상수 (Google 엔드포인트 URL 등):
  Settings에 두지 않음 → `app.domain.auth.google_constants` 참조.

환경 모델:
- `ENV=local` (기본): 편의적. 개발자 머신과 테스트용.
- `ENV=test`: local과 동일 편의성.
- `ENV=dev` / `ENV=prod`: 엄격. 불안전한 기본값을 거부.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Env = Literal["local", "test", "dev", "prod"]

_DEV_PROD = ("dev", "prod")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Runtime environment ──────────────────────────────────────────
    ENV: Env = "local"

    # ── Required secrets (no default — absence fails fast) ───────────
    DATABASE_URL: str = Field(...)
    JWT_SECRET: str = Field(..., min_length=32)
    GOOGLE_CLIENT_ID: str = Field(...)
    GOOGLE_CLIENT_SECRET: str = Field(...)

    # ── Database tunables ────────────────────────────────────────────
    DATABASE_ECHO: bool = False

    # ── Application metadata ─────────────────────────────────────────
    APP_NAME: str = "각할모 API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "각자 모여서 할거 하는 모임"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # NoDecode: pydantic-settings 가 기본적으로 list/dict 에 JSON decode 를 시도한다.
    # 우리는 CSV 로 받고 싶으므로 NoDecode 로 raw str 을 유지 → 아래 before-validator 가 분리.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # ── JWT ──────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # ── Security knobs ───────────────────────────────────────────────
    BCRYPT_ROUNDS: int = 12

    # ── Google OAuth (env-specific, 비시크릿) ─────────────────────────
    # REDIRECT_URI는 환경마다 다르므로 env로 유지 (로컬=http, 프로드=https).
    GOOGLE_REDIRECT_URI: str = (
        "http://localhost:8000/api/v1/auth/google/callback"
    )
    OAUTH_STATE_TTL_SECONDS: int = 600
    AUTH_ALLOW_GOOGLE_AUTOLINK: bool = False

    # ── Startup behaviour ────────────────────────────────────────────
    RUN_STARTUP_SEED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @model_validator(mode="after")
    def _enforce_prod_invariants(self) -> "Settings":
        if self.ENV not in _DEV_PROD:
            return self

        errors: list[str] = []

        if self.DEBUG:
            errors.append("DEBUG must be false in dev/prod.")
        if "localhost" in self.DATABASE_URL or "127.0.0.1" in self.DATABASE_URL:
            errors.append(
                "DATABASE_URL must not point to localhost in dev/prod."
            )
        if self.GOOGLE_REDIRECT_URI.startswith("http://"):
            errors.append(
                "GOOGLE_REDIRECT_URI must use HTTPS in dev/prod."
            )
        if self.RUN_STARTUP_SEED and self.ENV == "prod":
            errors.append(
                "RUN_STARTUP_SEED must be false in prod "
                "(use a dedicated Job)."
            )

        if errors:
            raise ValueError(
                "Insecure configuration for ENV="
                f"{self.ENV}: " + "; ".join(errors)
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.ENV == "prod"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
