"""Meeting 도메인 서비스 - 재사용 가능한 도메인 로직."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AlreadyParticipantError,
    CapacityExceededError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.domain.meeting.enums import (
    Goal,
    MeetingMode,
    MeetingStatus,
    ParticipantStatus,
)
from app.domain.meeting.models import Meeting, MeetingParticipant, MeetingSeries
from app.domain.meeting.repository import (
    MeetingRepository,
    MeetingSeriesRepository,
    next_occurrences,
)

# 모임 시작 24시간 전 이내에는 참여 취소 불가 — 노쇼 방지 정책.
LEAVE_CUTOFF_HOURS = 24


class MeetingService:
    """Meeting 엔티티를 위한 재사용 가능한 도메인 로직."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = MeetingRepository(session)

    # ========== 조회 ==========

    async def get_by_id(self, meeting_id: str) -> Meeting:
        meeting = await self.repository.get_by_id(meeting_id)
        if meeting is None:
            raise NotFoundError(detail="모임을 찾을 수 없습니다.")
        return meeting

    async def get_by_id_for_update(self, meeting_id: str) -> Meeting:
        meeting = await self.repository.get_by_id_for_update(meeting_id)
        if meeting is None:
            raise NotFoundError(detail="모임을 찾을 수 없습니다.")
        return meeting

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
        return await self.repository.list(
            offset=offset,
            limit=limit,
            mode=mode,
            region_id=region_id,
            goal=goal,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )

    async def list_by_host(
        self,
        host_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Meeting]:
        return await self.repository.list_by_host(host_id, offset=offset, limit=limit)

    async def list_by_participant(
        self,
        user_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
        status: ParticipantStatus | None = None,
    ) -> list[Meeting]:
        return await self.repository.list_by_participant(
            user_id, offset=offset, limit=limit, status=status
        )

    async def count_participants(
        self,
        meeting_id: str,
        *,
        status: ParticipantStatus | None = ParticipantStatus.APPROVED,
    ) -> int:
        return await self.repository.count_participants(meeting_id, status=status)

    # ========== 검증 ==========

    def ensure_host(self, meeting: Meeting, user_id: str) -> None:
        if meeting.host_id != user_id:
            raise ForbiddenError(detail="모임 호스트만 수행할 수 있는 작업입니다.")

    def ensure_recruiting(self, meeting: Meeting) -> None:
        if meeting.status is not MeetingStatus.RECRUITING:
            raise ForbiddenError(detail="모집 중인 모임이 아닙니다.")

    # ========== 명령 ==========

    async def create(self, meeting: Meeting) -> Meeting:
        return await self.repository.create(meeting)

    async def update(self, meeting: Meeting) -> Meeting:
        return await self.repository.update(meeting)

    async def delete(self, meeting: Meeting) -> None:
        await self.repository.soft_delete(meeting)

    async def join_with_lock(self, meeting_id: str, user_id: str) -> MeetingParticipant:
        """행 잠금 기반 참여 처리.

        흐름:
        1. `SELECT ... FOR UPDATE`로 meeting 행 잠금 (동시 join 직렬화)
        2. 상태/중복 검증 및 APPROVED 기준 정원 prelucheck
        3. status=PENDING으로 INSERT + 커밋

        승인은 호스트가 `approve_participant`로 명시적으로 수행.
        UNIQUE(meeting_id, user_id) 제약으로 이중 요청도 안전하게 차단.
        """
        try:
            meeting = await self.get_by_id_for_update(meeting_id)

            if meeting.host_id == user_id:
                raise AlreadyParticipantError(
                    detail="호스트는 이미 모임에 포함되어 있습니다."
                )
            self.ensure_recruiting(meeting)

            existing = await self.repository.get_participant(meeting.id, user_id)
            if existing is not None:
                raise AlreadyParticipantError(detail="이미 참여 중인 모임입니다.")

            approved = await self.repository.count_participants(
                meeting.id, status=ParticipantStatus.APPROVED
            )
            if approved >= meeting.max_participants:
                raise CapacityExceededError(detail="모임 정원이 가득 찼습니다.")

            participant = MeetingParticipant(
                meeting_id=meeting.id,
                user_id=user_id,
                status=ParticipantStatus.PENDING,
            )
            await self.repository.add_participant(participant)
        except IntegrityError as e:
            await self.session.rollback()
            raise AlreadyParticipantError(detail="이미 참여 중인 모임입니다.") from e
        except Exception:
            await self.session.rollback()
            raise

        await self.session.commit()
        await self.session.refresh(participant)

        # 호스트에게 참여 요청 알림.
        try:
            from app.domain.notification.enums import NotificationType
            from app.domain.notification.service import NotificationService

            await NotificationService(self.session).create(
                user_id=meeting.host_id,
                type=NotificationType.PARTICIPANT_PENDING,
                payload={
                    "meeting_id": meeting.id,
                    "meeting_title": meeting.title,
                    "participant_id": participant.id,
                    "user_id": user_id,
                },
            )
        except Exception:
            pass

        return participant

    async def leave(self, meeting_id: str, user_id: str) -> None:
        """탈퇴 처리 (호스트는 탈퇴 불가).

        시작 24시간 전 이내에는 탈퇴 차단 — 노쇼 방지 정책.
        """
        try:
            meeting = await self.get_by_id_for_update(meeting_id)

            if meeting.host_id == user_id:
                raise ForbiddenError(
                    detail="호스트는 모임을 떠날 수 없습니다. 모임을 삭제하거나 상태를 변경하세요."
                )

            # 24h time-guard — 시작 시각 - 현재 < 24h 이면 취소 불가.
            meeting_dt = datetime.combine(
                meeting.meeting_date, meeting.meeting_time, tzinfo=UTC
            )
            if meeting_dt - datetime.now(UTC) < timedelta(hours=LEAVE_CUTOFF_HOURS):
                raise ForbiddenError(
                    detail=(
                        f"모임 시작 {LEAVE_CUTOFF_HOURS}시간 이내에는 참여 취소가 불가능합니다. "
                        "호스트에게 문의해 주세요."
                    )
                )

            participant = await self.repository.get_participant(meeting.id, user_id)
            if participant is None:
                raise NotFoundError(detail="참여 정보를 찾을 수 없습니다.")

            was_approved = participant.status is ParticipantStatus.APPROVED
            await self.repository.remove_participant(participant)
        except Exception:
            await self.session.rollback()
            raise

        await self.session.commit()

        # 호스트에게 탈퇴 알림 — 이벤트 훅. 실패해도 본 흐름엔 영향 없음.
        # (늦은 커밋 이후라 트랜잭션 롤백 위험 없음)
        try:
            from app.domain.notification.enums import NotificationType
            from app.domain.notification.service import NotificationService

            await NotificationService(self.session).create(
                user_id=meeting.host_id,
                type=NotificationType.PARTICIPANT_LEFT,
                payload={
                    "meeting_id": meeting.id,
                    "user_id": user_id,
                    "was_approved": was_approved,
                },
            )
        except Exception:
            # 알림 실패가 탈퇴 자체를 뒤엎어서는 안 된다.
            pass

    # ========== 승인/거절 ==========

    async def approve_participant(
        self,
        meeting_id: str,
        participant_id: str,
        host_user_id: str,
    ) -> MeetingParticipant:
        """호스트가 대기 중인 참여자를 승인.

        - 호스트만 수행 가능
        - APPROVED 기준 정원 재검증 (동시 승인 경합 방지)
        - PENDING만 승인 가능 (이미 APPROVED/REJECTED 는 거절)
        """
        try:
            meeting = await self.get_by_id_for_update(meeting_id)
            self.ensure_host(meeting, host_user_id)

            participant = await self.repository.get_participant_by_id(participant_id)
            if participant is None or participant.meeting_id != meeting.id:
                raise NotFoundError(detail="참여 정보를 찾을 수 없습니다.")

            if participant.status is ParticipantStatus.APPROVED:
                raise ConflictError(detail="이미 승인된 참여자입니다.")
            if participant.status is ParticipantStatus.REJECTED:
                raise ConflictError(detail="이미 거절된 참여자입니다.")

            approved = await self.repository.count_participants(
                meeting.id, status=ParticipantStatus.APPROVED
            )
            if approved >= meeting.max_participants:
                raise CapacityExceededError(detail="모임 정원이 가득 찼습니다.")

            participant.status = ParticipantStatus.APPROVED
            participant.decided_at = datetime.now(UTC)
            await self.session.flush()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.commit()
        await self.session.refresh(participant)

        # 승인 알림 + 채팅방 세팅 이벤트 훅.
        try:
            from app.domain.chat.service import ChatService
            from app.domain.notification.enums import NotificationType
            from app.domain.notification.service import NotificationService

            await NotificationService(self.session).create(
                user_id=participant.user_id,
                type=NotificationType.PARTICIPANT_APPROVED,
                payload={
                    "meeting_id": meeting.id,
                    "meeting_title": meeting.title,
                },
            )

            # 채팅방: 처음 승인 시점에 room + host 가 생성되고,
            # 이번 승인된 참여자가 즉시 등록된다 (호스트도 idempotent).
            chat_svc = ChatService(self.session)
            room = await chat_svc.ensure_room_for_meeting(meeting.id)
            await chat_svc.ensure_participant(room.id, meeting.host_id)
            await chat_svc.ensure_participant(room.id, participant.user_id)
        except Exception:
            pass

        return participant

    async def reject_participant(
        self,
        meeting_id: str,
        participant_id: str,
        host_user_id: str,
    ) -> MeetingParticipant:
        """호스트가 대기 중인 참여자를 거절."""
        try:
            meeting = await self.get_by_id_for_update(meeting_id)
            self.ensure_host(meeting, host_user_id)

            participant = await self.repository.get_participant_by_id(participant_id)
            if participant is None or participant.meeting_id != meeting.id:
                raise NotFoundError(detail="참여 정보를 찾을 수 없습니다.")

            if participant.status is ParticipantStatus.REJECTED:
                raise ConflictError(detail="이미 거절된 참여자입니다.")

            participant.status = ParticipantStatus.REJECTED
            participant.decided_at = datetime.now(UTC)
            await self.session.flush()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.commit()
        await self.session.refresh(participant)

        # 거절 알림.
        try:
            from app.domain.notification.enums import NotificationType
            from app.domain.notification.service import NotificationService

            await NotificationService(self.session).create(
                user_id=participant.user_id,
                type=NotificationType.PARTICIPANT_REJECTED,
                payload={
                    "meeting_id": meeting.id,
                    "meeting_title": meeting.title,
                },
            )
        except Exception:
            pass

        return participant


class MeetingSeriesService:
    """정기 모임 시리즈 도메인 서비스.

    시리즈 생성 시 첫 N(기본 4) 회차의 Meeting 인스턴스를 함께 생성하고
    `series_id`로 링크한다.
    """

    DEFAULT_INITIAL_OCCURRENCES = 4

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = MeetingSeriesRepository(session)
        self.meeting_repository = MeetingRepository(session)

    # ========== 조회 ==========

    async def get_by_id(self, series_id: str) -> MeetingSeries:
        series = await self.repository.get_by_id(series_id)
        if series is None:
            raise NotFoundError(detail="정기 모임 시리즈를 찾을 수 없습니다.")
        return series

    async def list_by_host(
        self,
        host_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[MeetingSeries]:
        return await self.repository.list_by_host(host_id, offset=offset, limit=limit)

    # ========== 검증 ==========

    def ensure_host(self, series: MeetingSeries, user_id: str) -> None:
        if series.host_id != user_id:
            raise ForbiddenError(
                detail="시리즈 호스트만 수행할 수 있는 작업입니다."
            )

    # ========== 명령 ==========

    async def create_with_occurrences(
        self,
        series: MeetingSeries,
        *,
        count: int = DEFAULT_INITIAL_OCCURRENCES,
    ) -> MeetingSeries:
        """시리즈를 생성하고 첫 `count`회차 Meeting을 함께 insert.

        트랜잭션 경계:
        - series + meetings를 한 커밋에 묶어 원자성 보장
        - 실패 시 모두 롤백
        """
        try:
            self.session.add(series)
            await self.session.flush()
            await self.session.refresh(series)

            occurrence_dates = next_occurrences(
                series.start_date,
                series.frequency,
                count=count,
                end_date=series.end_date,
            )

            for occ_date in occurrence_dates:
                meeting = Meeting(
                    host_id=series.host_id,
                    series_id=series.id,
                    title=series.title,
                    mode=series.mode,
                    region_id=series.region_id,
                    location_name=series.location_name,
                    location_address=series.location_address,
                    meeting_date=occ_date,
                    meeting_time=series.meeting_time,
                    goal=series.goal,
                    max_participants=series.max_participants,
                    description=series.description,
                    is_recurring=True,
                )
                self.session.add(meeting)

            await self.session.flush()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.commit()
        await self.session.refresh(series)
        return series

    async def update(self, series: MeetingSeries) -> MeetingSeries:
        return await self.repository.update(series)

    async def delete(self, series: MeetingSeries) -> None:
        await self.repository.soft_delete(series)
