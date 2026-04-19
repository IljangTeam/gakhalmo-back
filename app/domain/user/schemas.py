"""User Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """사용자 공통 필드"""

    name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")
    email: EmailStr = Field(..., description="이메일 주소")
    profile_image: str | None = Field(None, description="프로필 이미지 URL")
    bio: str | None = Field(None, max_length=500, description="자기소개")

class UserSummary(BaseModel):
    """다른 응답에 포함되는 유저 요약 정보"""

    id: str
    name: str
    profile_image: str | None = None

    model_config = ConfigDict(from_attributes=True)

class UserCreate(UserBase):
    """유저 생성"""
    pass


class UserUpdate(BaseModel):
    """유저 업데이트 (모든 필드 Optional)"""

    name: str | None = Field(None, min_length=1, max_length=100)
    profile_image: str | None = None
    bio: str | None = Field(None, max_length=500)


class UserResponse(UserBase):
    """유저 정보 응답"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
