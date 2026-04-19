"""Meeting 도메인 enum 정의 (DB/Pydantic 공용, 인프라 의존성 없음)."""

from __future__ import annotations

import enum


class MeetingMode(str, enum.Enum):
    """모임 진행 방식."""

    OFFLINE = "offline"
    ONLINE = "online"


class Goal(str, enum.Enum):
    """모임 목표."""

    STUDY = "공부"
    WORK = "작업"
    READING = "독서"
    OTHER = "기타"


class MeetingStatus(str, enum.Enum):
    """모임 상태."""

    RECRUITING = "recruiting"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class ParticipantStatus(str, enum.Enum):
    """참여자 승인 상태."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RecurrenceFrequency(str, enum.Enum):
    """정기 모임 반복 주기."""

    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
