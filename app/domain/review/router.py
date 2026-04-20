"""Review + Attendance API router."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.dependencies import AsyncSessionDep
from app.domain.auth.dependencies import CurrentUserDep
from app.domain.notification.enums import NotificationType
from app.domain.notification.service import NotificationService
from app.domain.review.schemas import (
    AttendanceMarkRequest,
    AttendanceRateResponse,
    AttendanceResponse,
    ReviewCreate,
    ReviewResponse,
)
from app.domain.review.service import AttendanceService, ReviewService
from app.domain.user.service import UserService

router = APIRouter(tags=["Reviews"])


def _review_to_response(review, reviewer, reviewee) -> ReviewResponse:
    return ReviewResponse.model_validate(
        {
            "id": review.id,
            "meeting_id": review.meeting_id,
            "reviewer": reviewer,
            "reviewee": reviewee,
            "rating": review.rating,
            "content": review.content,
            "created_at": review.created_at,
        }
    )


@router.post(
    "/meetings/{meeting_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="모임 회고 작성",
)
async def create_review(
    meeting_id: str,
    data: ReviewCreate,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> ReviewResponse:
    svc = ReviewService(session)
    review = await svc.create(
        meeting_id=meeting_id, reviewer_id=current_user.id, data=data
    )
    user_svc = UserService(session)
    reviewer = current_user
    reviewee = await user_svc.get_by_id(data.reviewee_id)

    # 회고 작성 알림
    await NotificationService(session).create(
        user_id=data.reviewee_id,
        type=NotificationType.REVIEW_REQUESTED,
        payload={
            "meeting_id": meeting_id,
            "reviewer_id": current_user.id,
            "reviewer_name": current_user.name,
            "rating": data.rating,
        },
    )
    return _review_to_response(review, reviewer, reviewee)


@router.get(
    "/users/{user_id}/reviews",
    response_model=list[ReviewResponse],
    summary="특정 사용자가 받은 회고 목록",
)
async def list_reviews_for_user(
    user_id: str,
    session: AsyncSessionDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[ReviewResponse]:
    svc = ReviewService(session)
    rows = await svc.list_for_user(user_id, offset=offset, limit=limit)
    user_svc = UserService(session)
    out: list[ReviewResponse] = []
    for r in rows:
        reviewer = await user_svc.get_by_id(r.reviewer_id)
        reviewee = await user_svc.get_by_id(r.reviewee_id)
        out.append(_review_to_response(r, reviewer, reviewee))
    return out


@router.post(
    "/meetings/{meeting_id}/attendance/{user_id}",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="호스트가 참여자 출석/노쇼 마킹",
)
async def mark_attendance(
    meeting_id: str,
    user_id: str,
    data: AttendanceMarkRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> AttendanceResponse:
    svc = AttendanceService(session)
    record = await svc.mark(
        meeting_id=meeting_id,
        user_id=user_id,
        host_user_id=current_user.id,
        status=data.status,
    )
    return AttendanceResponse.model_validate(record)


@router.get(
    "/users/{user_id}/attendance-rate",
    response_model=AttendanceRateResponse,
    summary="사용자 출석률 조회",
)
async def get_attendance_rate(
    user_id: str,
    session: AsyncSessionDep,
) -> AttendanceRateResponse:
    svc = AttendanceService(session)
    data = await svc.rate_for_user(user_id)
    return AttendanceRateResponse.model_validate(data)
