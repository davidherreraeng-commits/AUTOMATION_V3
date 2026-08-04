from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from application.services.authentication_service import (
    AuthenticationService,
    InactiveUserError,
    InvalidCredentialsError,
    PasswordPolicyError,
)
from infrastructure.config.settings import Settings
from infrastructure.security.jwt_service import JWTService
from interfaces.api.dependencies import (
    CurrentUser,
    get_authentication_service,
    get_jwt_service,
    get_settings,
)
from interfaces.api.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    UserSessionResponse,
)


router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    data: LoginRequest,
    response: Response,
    auth: Annotated[
        AuthenticationService,
        Depends(get_authentication_service),
    ],
    tokens: Annotated[JWTService, Depends(get_jwt_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    try:
        user = auth.authenticate(
            username=data.username,
            password=data.password,
        )
    except (InvalidCredentialsError, InactiveUserError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    token = tokens.create_access_token(user)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token.value,
        max_age=settings.access_token_minutes * 60,
        expires=token.expires_at,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )

    return LoginResponse(
        user=UserSessionResponse.from_user(user),
        expires_at=token.expires_at,
    )


@router.get("/me", response_model=UserSessionResponse)
def get_me(user: CurrentUser) -> UserSessionResponse:
    return UserSessionResponse.from_user(user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    return MessageResponse(message="Sesión cerrada correctamente.")


@router.post("/change-password", response_model=UserSessionResponse)
def change_password(
    data: ChangePasswordRequest,
    user: CurrentUser,
    auth: Annotated[
        AuthenticationService,
        Depends(get_authentication_service),
    ],
) -> UserSessionResponse:
    try:
        updated = auth.change_password(
            user=user,
            current_password=data.current_password,
            new_password=data.new_password,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta.",
        ) from error
    except PasswordPolicyError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return UserSessionResponse.from_user(updated)
