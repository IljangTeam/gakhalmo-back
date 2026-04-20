"""User API router — 공개 프로필 조회만 제공.

운영 요구사항 상 비인증 생성/목록/수정/삭제 엔드포인트는 제거되었다.
자기 자신 프로필 편집은 `PATCH /auth/me`, 신규 유저 생성은 `POST /auth/register` 로 수행한다.
"""

from fastapi import APIRouter

from app.domain.user.schemas import UserResponse
from app.domain.user.usecases import GetUserUseCaseDep

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="사용자 공개 프로필 조회",
)
async def get_user(
    user_id: str,
    use_case: GetUserUseCaseDep,
) -> UserResponse:
    user = await use_case.execute(user_id)
    return UserResponse.model_validate(user)
