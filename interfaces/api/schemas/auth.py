from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from domain.models.user_account import UserAccount


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El usuario es obligatorio.")
        return normalized


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    dependency: str
    role: str
    is_superuser: bool
    must_change_password: bool

    @classmethod
    def from_user(cls, user: UserAccount) -> "UserSessionResponse":
        return cls(
            id=user.user_id,
            username=user.username,
            dependency=user.dependency,
            role=user.role.value,
            is_superuser=user.is_superuser,
            must_change_password=user.must_change_password,
        )


class LoginResponse(BaseModel):
    user: UserSessionResponse
    expires_at: datetime


class MessageResponse(BaseModel):
    message: str
