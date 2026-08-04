from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from application.services.user_management_service import (
    TemporaryPasswordPolicyError,
    UserManagementService,
)
from domain.errors.user_errors import (
    CannotDeactivateOwnAccountError,
    CannotResetOwnPasswordError,
    UserAlreadyExistsError,
    UserManagementPermissionError,
    UserNotFoundError,
)
from interfaces.api.dependencies import (
    Superuser,
    get_user_management_service,
)
from interfaces.api.schemas.users import (
    CreateUserRequest,
    ResetUserPasswordRequest,
    UpdateUserStatusRequest,
    UserListResponse,
    UserResponse,
)


router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("", response_model=UserListResponse)
def list_users(
    actor: Superuser,
    service: Annotated[
        UserManagementService,
        Depends(get_user_management_service),
    ],
) -> UserListResponse:
    users = service.list_users(actor=actor)
    items = [UserResponse.from_user(user) for user in users]
    return UserListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    data: CreateUserRequest,
    actor: Superuser,
    service: Annotated[
        UserManagementService,
        Depends(get_user_management_service),
    ],
) -> UserResponse:
    try:
        user = service.create_user(
            actor=actor,
            username=data.username,
            temporary_password=data.temporary_password,
            role=data.role,
        )
    except UserAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except TemporaryPasswordPolicyError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except UserManagementPermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

    return UserResponse.from_user(user)


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int,
    data: UpdateUserStatusRequest,
    actor: Superuser,
    service: Annotated[
        UserManagementService,
        Depends(get_user_management_service),
    ],
) -> UserResponse:
    try:
        user = service.set_user_active(
            actor=actor,
            target_user_id=user_id,
            is_active=data.is_active,
        )
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el usuario solicitado.",
        ) from error
    except CannotDeactivateOwnAccountError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return UserResponse.from_user(user)


@router.post("/{user_id}/reset-password", response_model=UserResponse)
def reset_user_password(
    user_id: int,
    data: ResetUserPasswordRequest,
    actor: Superuser,
    service: Annotated[
        UserManagementService,
        Depends(get_user_management_service),
    ],
) -> UserResponse:
    try:
        user = service.reset_password(
            actor=actor,
            target_user_id=user_id,
            temporary_password=data.temporary_password,
        )
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el usuario solicitado.",
        ) from error
    except CannotResetOwnPasswordError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except TemporaryPasswordPolicyError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return UserResponse.from_user(user)
