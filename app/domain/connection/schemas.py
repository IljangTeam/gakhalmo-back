"""Connection Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.connection.enums import ConnectionStatus
from app.domain.user.schemas import UserSummary


class ConnectionResponse(BaseModel):
    id: str
    follower: UserSummary
    following: UserSummary
    status: ConnectionStatus
    created_at: datetime
    accepted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
