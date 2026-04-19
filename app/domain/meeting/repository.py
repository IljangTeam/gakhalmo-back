"""Meeting repository for database operations.

트랜잭션 정책:
- 단일 쓰기 연산(`create`/`update`/`soft_delete`)은 자체 커밋으로 종결
- 참여자 추가/삭제는 유스케이스가 트랜잭션 경계를 잡을 수 있도록
  `flush` 기반으로 제공 (`add_participant`, `remove_participant`)

소프트 삭제:
- 모든 조회는 기본적으로 `Meeting.deleted_at IS NULL` 필터를 적용.
- 하드 삭제 대신 `soft_delete`를 사용해 이력과 FK 참조 무결성을 유지.
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.meeting.enums import (
    Goal,
    MeetingMode,
    MeetingStatus,
    ParticipantStatus,
    RecurrenceFrequency,
)
from app.domain.meeting.models import (
    Meeting,
    MeetingParticipant,
    MeetingSeries,
    _generate_ulid,
)


class MeetingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ===== Meeting =====

    async def create(self, meeting: Meeting) -> Meeting:
        self.session.add(meeting)
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting

    async def get_by_id(self, meeting_id: str) -> Meeting | None:
        result = await self.session.execute(
            select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, meeting_id: str) -> Meeting | None:
        """참여자 추가/삭제 경합 방지를 위한 행 단위 잠금 조회."""
        result = await self.session.execute(
            select(Meeting)
            .where(
                Meeting.id == meeting_id,
                Meeting.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        mode: MeetingMode | None = None,
        region_id: int | None = None,
        goal: Goal | None = None,
        status: MeetingStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Meeting]:
        stmt = select(Meeting).where(Meeting.deleted_at.is_(None))
        if mode is not None:
            stmt = stmt.where(Meeting.mode == mode)
        if region_id is not None:
            stmt = stmt.where(Meeting.region_id == region_id)
        if goal is not None:
            stmt = stmt.where(Meeting.goal == goal)
        if status is not None:
            stmt = stmt.where(Meeting.status == status)
        if date_from is not None:
            stmt = stmt.where(Meeting.meeting_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Meeting.meeting_date <= date_to)

        stmt = (
            stmt.order_by(Meeting.meeting_date.asc(), Meeting.meeting_time.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_host(
        self,
        host_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Meeting]:
        result = await self.session.execute(
            select(Meeting)
            .where(
                Meeting.host_id == host_id,
                Meeting.deleted_at.is_(None),
            )
            .order_by(Meeting.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_participant(
        self,
        user_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
        status: ParticipantStatus | None = None,
    ) -> list[Meeting]:
        stmt = (
            select(Meeting)
            .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
            .where(
                MeetingParticipant.user_id == user_id,
                Meeting.deleted_at.is_(None),
            )
        )
        if status is not None:
            stmt = stmt.where(MeetingParticipant.status == status)

        stmt = (
            stmt.order_by(Meeting.meeting_date.asc(), Meeting.meeting_time.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, meeting: Meeting) -> Meeting:
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting

    async def soft_delete(self, meeting: Meeting) -> None:
        """논리 삭제 — `deleted_at`만 설정. 참여자/이력/FK 관계는 보존."""
        meeting.deleted_at = datetime.now(UTC)
        meeting.active_guard = _generate_ulid()
        await self.session.commit()

    # ===== Participants =====

    async def count_participants(
        self,
        meeting_id: str,
        *,
        status: ParticipantStatus | None = ParticipantStatus.APPROVED,
    ) -> int:
        """참여자 수 조회.

        기본적으로 정원 로직에서 사용하므로 `APPROVED` 상태만 집계한다.
        `status=None`을 전달하면 PENDING/REJECTED 포함 전체 건수를 반환.
        """
        stmt = select(func.count()).select_from(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        if status is not None:
            stmt = stmt.where(MeetingParticipant.status == status)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_participant(
        self,
        meeting_id: str,
        user_id: str,
    ) -> MeetingParticipant | None:
        result = await self.session.execute(
            select(MeetingParticipant).where(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_participant_by_id(
        self,
        participant_id: str,
    ) -> MeetingParticipant | None:
        result = await self.session.execute(
            select(MeetingParticipant).where(
                MeetingParticipant.id == participant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_participants(
        self,
        meeting_id: str,
        *,
        status: ParticipantStatus | None = None,
    ) -> list[MeetingParticipant]:
        stmt = select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        if status is not None:
            stmt = stmt.where(MeetingParticipant.status == status)
        stmt = stmt.order_by(MeetingParticipant.joined_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_participant(
        self,
        participant: MeetingParticipant,
    ) -> MeetingParticipant:
        """참여자 추가 (flush만 수행 — 커밋은 호출 측 트랜잭션이 책임)."""
        self.session.add(participant)
        await self.session.flush()
        await self.session.refresh(participant)
        return participant

    async def remove_participant(self, participant: MeetingParticipant) -> None:
        """참여자 삭제 (flush만 수행 — 커밋은 호출 측 트랜잭션이 책임)."""
        await self.session.delete(participant)
        await self.session.flush()


class MeetingSeriesRepository:
    """정기 모임 시리즈 레포지토리.

    Meeting과 동일하게 deleted_at 기반 소프트 삭제를 적용한다.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, series: MeetingSeries) -> MeetingSeries:
        self.session.add(series)
        await self.session.commit()
        await self.session.refresh(series)
        return series

    async def add(self, series: MeetingSeries) -> MeetingSeries:
        """flush만 수행. 커밋은 호출 측이 책임."""
        self.session.add(series)
        await self.session.flush()
        await self.session.refresh(series)
        return series

    async def get_by_id(self, series_id: str) -> MeetingSeries | None:
        result = await self.session.execute(
            select(MeetingSeries).where(
                MeetingSeries.id == series_id,
                MeetingSeries.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_host(
        self,
        host_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[MeetingSeries]:
        result = await self.session.execute(
            select(MeetingSeries)
            .where(
                MeetingSeries.host_id == host_id,
                MeetingSeries.deleted_at.is_(None),
            )
            .order_by(MeetingSeries.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, series: MeetingSeries) -> MeetingSeries:
        await self.session.commit()
        await self.session.refresh(series)
        return series

    async def soft_delete(self, series: MeetingSeries) -> None:
        series.deleted_at = datetime.now(UTC)
        await self.session.commit()


def _add_months(base: date, months: int) -> date:
    """Calendar arithmetic: base 날짜에 `months`를 더한 date 반환.

    월말 경계(예: 1월 31일 + 1개월) 처리를 위해 대상 월의 실제 일 수로 클램핑한다.
    """
    if months == 0:
        return base
    year = base.year + (base.month - 1 + months) // 12
    month = (base.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(base.day, last_day)
    return date(year, month, day)


def next_occurrences(
    start_date: date,
    frequency: RecurrenceFrequency,
    *,
    count: int = 4,
    end_date: date | None = None,
) -> list[date]:
    """시리즈 시작일 기준으로 `count` 개의 다음 발생 일자를 계산.

    첫 번째 항목은 start_date 그 자체. end_date가 지정된 경우 그 이후 일자는 제외.
    """
    if count <= 0:
        return []

    occurrences: list[date] = []
    for i in range(count):
        if frequency is RecurrenceFrequency.WEEKLY:
            occ = start_date + timedelta(days=7 * i)
        elif frequency is RecurrenceFrequency.BIWEEKLY:
            occ = start_date + timedelta(days=14 * i)
        elif frequency is RecurrenceFrequency.MONTHLY:
            occ = _add_months(start_date, i)
        else:  # pragma: no cover - enum exhaustive
            raise ValueError(f"Unsupported frequency: {frequency}")

        if end_date is not None and occ > end_date:
            break
        occurrences.append(occ)
    return occurrences
