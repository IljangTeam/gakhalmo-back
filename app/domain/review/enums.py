"""Review / Attendance enums."""

from enum import StrEnum


class AttendanceStatus(StrEnum):
    """모임 출석 상태 — 호스트가 사후에 마킹."""

    ATTENDED = "attended"
    NO_SHOW = "no_show"
