"""Auth 도메인 enum (DB/Pydantic 공용, 인프라 의존성 없음)."""

from __future__ import annotations

import enum


class AuthProvider(str, enum.Enum):
    """인증 제공자 — 로컬 회원가입 또는 외부 OAuth."""

    LOCAL = "local"
    GOOGLE = "google"
