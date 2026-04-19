"""User API router."""

from fastapi import APIRouter, Query, status

from app.domain.user.schemas import UserCreate, UserResponse, UserUpdate
from app.domain.user.usecases import CreateUserUseCaseDep, DeleteUserUseCaseDep, GetUserUseCaseDep, ListUsersUseCaseDep, UpdateUserUseCaseDep

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="사용자 생성",
)
async def create_user(
    data: UserCreate,
    use_case: CreateUserUseCaseDep
) -> UserResponse:
    """Create a new user."""
    user = await use_case.execute(data)
    return UserResponse.model_validate(user)


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="사용자 목록 조회",
)
async def list_users(
    use_case: ListUsersUseCaseDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[UserResponse]:
    users = await use_case.execute(offset=offset, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="사용자 상세 조회",
)
async def get_user(
    user_id: str,
    use_case: GetUserUseCaseDep
) -> UserResponse:
    user = await use_case.execute(user_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="사용자 정보 수정",
)
async def update_user(
    user_id: str,
    data: UserUpdate,
    use_case: UpdateUserUseCaseDep,
) -> UserResponse:
    user = await use_case.execute(user_id, data)
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="사용자 삭제",
)
async def delete_user(
    user_id: str,
    use_case: DeleteUserUseCaseDep
) -> None:
    await use_case.execute(user_id)
