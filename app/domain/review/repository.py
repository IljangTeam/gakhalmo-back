"""Review + Attendance repositories."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.review.enums import AttendanceStatus
from app.domain.review.models import MeetingAttendance, Review


class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, review: Review) -> Review:
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def get_for_pair(
        self, meeting_id: str, reviewer_id: str, reviewee_id: str
    ) -> Review | None:
        result = await self.session.execute(
            select(Review).where(
                Review.meeting_id == meeting_id,
                Review.reviewer_id == reviewer_id,
                Review.reviewee_id == reviewee_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_reviewee(
        self,
        reviewee_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Review]:
        result = await self.session.execute(
            select(Review)
            .where(Review.reviewee_id == reviewee_id)
            .order_by(Review.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


class AttendanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, record: MeetingAttendance) -> MeetingAttendance:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_for_pair(
        self, meeting_id: str, user_id: str
    ) -> MeetingAttendance | None:
        result = await self.session.execute(
            select(MeetingAttendance).where(
                MeetingAttendance.meeting_id == meeting_id,
                MeetingAttendance.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_by_status(self, user_id: str) -> dict[AttendanceStatus, int]:
        """(status → count) 맵. 기록 없는 status 는 0."""
        result = await self.session.execute(
            select(MeetingAttendance.status, func.count(MeetingAttendance.id))
            .where(MeetingAttendance.user_id == user_id)
            .group_by(MeetingAttendance.status)
        )
        out: dict[AttendanceStatus, int] = {s: 0 for s in AttendanceStatus}
        for status, count in result.all():
            out[status] = int(count)
        return out
