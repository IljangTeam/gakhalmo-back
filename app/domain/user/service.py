"""사용자 도메인 서비스 - 재사용 가능한 도메인 로직."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.user.models import User
from app.domain.user.repository import UserRepository


class UserService:
    """User 엔티티를 위한 재사용 가능한 도메인 로직."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)

    # ========== 조회 연산 ==========

    async def get_by_id(self, user_id: str) -> User:
        """ID로 사용자 조회. 없으면 NotFoundError 발생."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(detail="사용자를 찾을 수 없습니다.")
        return user

    async def get_by_id_or_none(self, user_id: str) -> User | None:
        """ID로 사용자 조회. 없으면 None 반환."""
        return await self.repository.get_by_id(user_id)

    async def get_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회."""
        return await self.repository.get_by_email(email)

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """페이지네이션 기반 전체 사용자 조회."""
        return await self.repository.get_all(offset=offset, limit=limit)

    async def exists_by_email(self, email: str) -> bool:
        """이메일로 사용자 존재 여부 확인."""
        user = await self.repository.get_by_email(email)
        return user is not None

    # ========== 검증 로직 ==========

    async def validate_email_unique(self, email: str, exclude_user_id: str | None = None) -> None:
        """이메일 중복 검증. 중복이면 ConflictError 발생.

        Args:
            email: 검증할 이메일
            exclude_user_id: 검증에서 제외할 사용자 ID (수정 시 본인 제외용)
        """
        existing = await self.repository.get_by_email(email)
        if existing and (exclude_user_id is None or existing.id != exclude_user_id):
            raise ConflictError(detail="이미 등록된 이메일입니다.")

    # ========== 명령 연산 ==========

    async def create(self, user: User) -> User:
        """신규 사용자 엔티티 영속화."""
        return await self.repository.create(user)

    async def update(self, user: User) -> User:
        """사용자 엔티티 변경 사항 영속화."""
        return await self.repository.update(user)

    async def delete(self, user: User) -> None:
        """사용자 엔티티 삭제."""
        await self.repository.delete(user)
