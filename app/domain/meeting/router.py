"""Meeting API router."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, status

from app.domain.auth.dependencies import CurrentUserDep
from app.domain.meeting.enums import Goal, MeetingMode, MeetingStatus
from app.domain.meeting.models import Meeting, MeetingSeries
from app.domain.meeting.schemas import (
    MeetingCreate,
    MeetingDetailResponse,
    MeetingParticipantResponse,
    MeetingResponse,
    MeetingSeriesCreateRequest,
    MeetingSeriesResponse,
    MeetingSeriesUpdateRequest,
    MeetingUpdate,
    ParticipantStatusUpdateRequest,
)
from app.domain.meeting.usecases import (
    ApproveParticipantUseCaseDep,
    CreateMeetingUseCaseDep,
    CreateSeriesUseCaseDep,
    DeleteMeetingUseCaseDep,
    DeleteSeriesUseCaseDep,
    GetMeetingUseCaseDep,
    GetSeriesUseCaseDep,
    JoinMeetingUseCaseDep,
    LeaveMeetingUseCaseDep,
    ListMeetingsByHostUseCaseDep,
    ListMeetingsByParticipantUseCaseDep,
    ListMeetingsUseCaseDep,
    ListSeriesByHostUseCaseDep,
    RejectParticipantUseCaseDep,
    UpdateMeetingUseCaseDep,
    UpdateSeriesUseCaseDep,
)

router = APIRouter(prefix="/meetings", tags=["Meetings"])


def _to_response(meeting: Meeting) -> MeetingResponse:
    return MeetingResponse.model_validate(
        {
            "id": meeting.id,
            "title": meeting.title,
            "mode": meeting.mode,
            "region": meeting.region,
            "location_name": meeting.location_name,
            "location_address": meeting.location_address,
            "meeting_date": meeting.meeting_date,
            "meeting_time": meeting.meeting_time,
            "goal": meeting.goal,
            "max_participants": meeting.max_participants,
            "current_participants": len(meeting.participants),
            "description": meeting.description,
            "is_recurring": meeting.is_recurring,
            "status": meeting.status,
            "series_id": meeting.series_id,
            "host": meeting.host,
            "created_at": meeting.created_at,
            "updated_at": meeting.updated_at,
        }
    )


def _to_detail_response(meeting: Meeting) -> MeetingDetailResponse:
    base = _to_response(meeting).model_dump()
    base["participants"] = [
        MeetingParticipantResponse.model_validate(p) for p in meeting.participants
    ]
    return MeetingDetailResponse.model_validate(base)


def _to_series_response(series: MeetingSeries) -> MeetingSeriesResponse:
    return MeetingSeriesResponse.model_validate(
        {
            "id": series.id,
            "title": series.title,
            "description": series.description,
            "mode": series.mode,
            "region": series.region,
            "location_name": series.location_name,
            "location_address": series.location_address,
            "goal": series.goal,
            "max_participants": series.max_participants,
            "frequency": series.frequency,
            "start_date": series.start_date,
            "end_date": series.end_date,
            "meeting_time": series.meeting_time,
            "is_active": series.is_active,
            "host": series.host,
            "created_at": series.created_at,
            "updated_at": series.updated_at,
        }
    )


# ========== Series endpoints (상위 경로 충돌 방지 위해 /{meeting_id} 이전에 선언) ==========


@router.post(
    "/series",
    response_model=MeetingSeriesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="정기 모임 시리즈 생성",
)
async def create_series(
    data: MeetingSeriesCreateRequest,
    current_user: CurrentUserDep,
    use_case: CreateSeriesUseCaseDep,
) -> MeetingSeriesResponse:
    series = await use_case.execute(current_user.id, data)
    return _to_series_response(series)


@router.get(
    "/series",
    response_model=list[MeetingSeriesResponse],
    summary="호스트별 정기 모임 시리즈 목록",
)
async def list_series(
    host_id: str,
    use_case: ListSeriesByHostUseCaseDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[MeetingSeriesResponse]:
    rows = await use_case.execute(host_id, offset=offset, limit=limit)
    return [_to_series_response(s) for s in rows]


@router.get(
    "/series/{series_id}",
    response_model=MeetingSeriesResponse,
    summary="정기 모임 시리즈 단건 조회",
)
async def get_series(
    series_id: str,
    use_case: GetSeriesUseCaseDep,
) -> MeetingSeriesResponse:
    series = await use_case.execute(series_id)
    return _to_series_response(series)


@router.patch(
    "/series/{series_id}",
    response_model=MeetingSeriesResponse,
    summary="정기 모임 시리즈 수정 (호스트 전용)",
)
async def update_series(
    series_id: str,
    data: MeetingSeriesUpdateRequest,
    current_user: CurrentUserDep,
    use_case: UpdateSeriesUseCaseDep,
) -> MeetingSeriesResponse:
    series = await use_case.execute(series_id, current_user.id, data)
    return _to_series_response(series)


@router.delete(
    "/series/{series_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="정기 모임 시리즈 삭제 (호스트 전용)",
)
async def delete_series(
    series_id: str,
    current_user: CurrentUserDep,
    use_case: DeleteSeriesUseCaseDep,
) -> None:
    await use_case.execute(series_id, current_user.id)


# ========== Meeting endpoints ==========


@router.post(
    "/",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="모임 개설",
)
async def create_meeting(
    data: MeetingCreate,
    current_user: CurrentUserDep,
    use_case: CreateMeetingUseCaseDep,
) -> MeetingResponse:
    meeting = await use_case.execute(current_user.id, data)
    return _to_response(meeting)


@router.get(
    "/",
    response_model=list[MeetingResponse],
    summary="모임 목록 조회 (필터 지원)",
)
async def list_meetings(
    use_case: ListMeetingsUseCaseDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    mode: MeetingMode | None = Query(None, description="온/오프라인 필터"),
    region_id: int | None = Query(None, description="지역 ID 필터 (regions.id)"),
    goal: Goal | None = Query(None, description="목표 필터"),
    status_: MeetingStatus | None = Query(
        None, alias="status", description="모임 상태"
    ),
    date_from: date | None = Query(None, description="시작 날짜"),
    date_to: date | None = Query(None, description="종료 날짜"),
) -> list[MeetingResponse]:
    meetings = await use_case.execute(
        offset=offset,
        limit=limit,
        mode=mode,
        region_id=region_id,
        goal=goal,
        status=status_,
        date_from=date_from,
        date_to=date_to,
    )
    return [_to_response(m) for m in meetings]


@router.get(
    "/hosted/{host_id}",
    response_model=list[MeetingResponse],
    summary="호스트가 개설한 모임 목록",
)
async def list_hosted_meetings(
    host_id: str,
    use_case: ListMeetingsByHostUseCaseDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[MeetingResponse]:
    meetings = await use_case.execute(host_id, offset=offset, limit=limit)
    return [_to_response(m) for m in meetings]


@router.get(
    "/participated/{user_id}",
    response_model=list[MeetingResponse],
    summary="참여 중인 모임 목록",
)
async def list_participated_meetings(
    user_id: str,
    use_case: ListMeetingsByParticipantUseCaseDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[MeetingResponse]:
    meetings = await use_case.execute(user_id, offset=offset, limit=limit)
    return [_to_response(m) for m in meetings]


@router.get(
    "/{meeting_id}",
    response_model=MeetingDetailResponse,
    summary="모임 상세 조회",
)
async def get_meeting(
    meeting_id: str,
    use_case: GetMeetingUseCaseDep,
) -> MeetingDetailResponse:
    meeting = await use_case.execute(meeting_id)
    return _to_detail_response(meeting)


@router.patch(
    "/{meeting_id}",
    response_model=MeetingResponse,
    summary="모임 정보 수정 (호스트 전용)",
)
async def update_meeting(
    meeting_id: str,
    data: MeetingUpdate,
    current_user: CurrentUserDep,
    use_case: UpdateMeetingUseCaseDep,
) -> MeetingResponse:
    meeting = await use_case.execute(meeting_id, current_user.id, data)
    return _to_response(meeting)


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="모임 삭제 (호스트 전용)",
)
async def delete_meeting(
    meeting_id: str,
    current_user: CurrentUserDep,
    use_case: DeleteMeetingUseCaseDep,
) -> None:
    await use_case.execute(meeting_id, current_user.id)


@router.post(
    "/{meeting_id}/participants",
    response_model=MeetingParticipantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="모임 참여 (PENDING 상태로 생성)",
)
async def join_meeting(
    meeting_id: str,
    current_user: CurrentUserDep,
    use_case: JoinMeetingUseCaseDep,
) -> MeetingParticipantResponse:
    participant = await use_case.execute(meeting_id, current_user.id)
    return MeetingParticipantResponse.model_validate(participant)


@router.delete(
    "/{meeting_id}/participants/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="모임 탈퇴",
)
async def leave_meeting(
    meeting_id: str,
    current_user: CurrentUserDep,
    use_case: LeaveMeetingUseCaseDep,
) -> None:
    await use_case.execute(meeting_id, current_user.id)


@router.post(
    "/{meeting_id}/participants/{participant_id}/approve",
    response_model=MeetingParticipantResponse,
    summary="참여 승인 (호스트 전용)",
)
async def approve_participant(
    meeting_id: str,
    participant_id: str,
    current_user: CurrentUserDep,
    use_case: ApproveParticipantUseCaseDep,
    data: ParticipantStatusUpdateRequest | None = None,  # noqa: ARG001
) -> MeetingParticipantResponse:
    participant = await use_case.execute(meeting_id, participant_id, current_user.id)
    return MeetingParticipantResponse.model_validate(participant)


@router.post(
    "/{meeting_id}/participants/{participant_id}/reject",
    response_model=MeetingParticipantResponse,
    summary="참여 거절 (호스트 전용)",
)
async def reject_participant(
    meeting_id: str,
    participant_id: str,
    current_user: CurrentUserDep,
    use_case: RejectParticipantUseCaseDep,
    data: ParticipantStatusUpdateRequest | None = None,  # noqa: ARG001
) -> MeetingParticipantResponse:
    participant = await use_case.execute(meeting_id, participant_id, current_user.id)
    return MeetingParticipantResponse.model_validate(participant)
