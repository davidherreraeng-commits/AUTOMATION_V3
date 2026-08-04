from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from domain.enums.user_role import UserRole
from domain.models.user_account import UserAccount


_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    temporary_password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.OPERATOR

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El usuario es obligatorio.")
        if not _USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError(
                "El usuario solo puede contener letras, números, punto, "
                "guion y guion bajo."
            )
        return normalized


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class ResetUserPasswordRequest(BaseModel):
    temporary_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    dependency: str
    role: str
    is_superuser: bool
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_user(cls, user: UserAccount) -> "UserResponse":
        return cls(
            id=user.user_id,
            username=user.username,
            dependency=user.dependency,
            role=user.role.value,
            is_superuser=user.is_superuser,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
        )


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
