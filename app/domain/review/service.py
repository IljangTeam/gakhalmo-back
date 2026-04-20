"""Review + Attendance domain services."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.domain.meeting.enums import ParticipantStatus
from app.domain.meeting.service import MeetingService
from app.domain.review.enums import AttendanceStatus
from app.domain.review.models import MeetingAttendance, Review
from app.domain.review.repository import AttendanceRepository, ReviewRepository
from app.domain.review.schemas import ReviewCreate
from app.domain.user.service import UserService


class ReviewService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ReviewRepository(session)

    async def create(
        self,
        *,
        meeting_id: str,
        reviewer_id: str,
        data: ReviewCreate,
    ) -> Review:
        if data.reviewee_id == reviewer_id:
            raise BadRequestError(detail="본인에게는 회고를 남길 수 없습니다.")

        meeting_service = MeetingService(self.session)
        meeting = await meeting_service.get_by_id(meeting_id)

        # 양쪽 모두 모임에 속해있어야 한다 (호스트 or APPROVED 참여자).
        def _is_member(uid: str) -> bool:
            if meeting.host_id == uid:
                return True
            return any(
                p.user_id == uid and p.status is ParticipantStatus.APPROVED
                for p in meeting.participants
            )

        if not _is_member(reviewer_id):
            raise ForbiddenError(detail="모임 참여자만 회고를 작성할 수 있습니다.")
        if not _is_member(data.reviewee_id):
            raise BadRequestError(detail="회고 대상이 해당 모임 참여자가 아닙니다.")

        # 중복 방지 — DB UNIQUE 로도 막히지만 의도적 409 응답을 위해 사전 조회.
        existing = await self.repository.get_for_pair(
            meeting_id, reviewer_id, data.reviewee_id
        )
        if existing is not None:
            raise ConflictError(detail="이미 회고를 작성했습니다.")

        review = Review(
            meeting_id=meeting_id,
            reviewer_id=reviewer_id,
            reviewee_id=data.reviewee_id,
            rating=data.rating,
            content=data.content,
        )
        return await self.repository.create(review)

    async def list_for_user(
        self, user_id: str, *, offset: int = 0, limit: int = 20
    ) -> list[Review]:
        await UserService(self.session).get_by_id(user_id)  # 존재 검증
        return await self.repository.list_for_reviewee(
            user_id, offset=offset, limit=limit
        )


class AttendanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = AttendanceRepository(session)

    async def mark(
        self,
        *,
        meeting_id: str,
        user_id: str,
        host_user_id: str,
        status: AttendanceStatus,
    ) -> MeetingAttendance:
        meeting_service = MeetingService(self.session)
        meeting = await meeting_service.get_by_id(meeting_id)
        meeting_service.ensure_host(meeting, host_user_id)

        # 대상 user 가 해당 모임의 APPROVED 참여자여야 한다.
        approved_ids = {
            p.user_id
            for p in meeting.participants
            if p.status is ParticipantStatus.APPROVED
        }
        if user_id not in approved_ids:
            raise BadRequestError(
                detail="APPROVED 참여자만 출석 기록을 남길 수 있습니다."
            )

        existing = await self.repository.get_for_pair(meeting_id, user_id)
        if existing is not None:
            raise ConflictError(detail="이미 출석 기록이 있습니다.")

        record = MeetingAttendance(
            meeting_id=meeting_id,
            user_id=user_id,
            status=status,
            marked_by=host_user_id,
        )
        return await self.repository.create(record)

    async def rate_for_user(self, user_id: str) -> dict:
        await UserService(self.session).get_by_id(user_id)
        counts = await self.repository.count_by_status(user_id)
        attended = counts.get(AttendanceStatus.ATTENDED, 0)
        no_show = counts.get(AttendanceStatus.NO_SHOW, 0)
        total = attended + no_show
        rate = (attended / total) if total > 0 else 0.0
        return {
            "user_id": user_id,
            "attended": attended,
            "total_recorded": total,
            "rate": rate,
        }


def _raise_if_not_found(v: object | None, detail: str) -> None:
    if v is None:
        raise NotFoundError(detail=detail)
