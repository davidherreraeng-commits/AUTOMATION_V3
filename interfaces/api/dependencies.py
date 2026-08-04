from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from adapters.persistence.sqlite.batch_repository import SQLiteBatchRepository
from adapters.persistence.sqlite.portal_credential_repository import (
    SQLitePortalCredentialRepository,
)
from adapters.persistence.sqlite.user_repository import SQLiteUserRepository
from application.ports.batch_repository import BatchRepository
from application.ports.contract_file_validator import ContractFileValidator
from application.ports.credential_cipher import CredentialCipher
from application.ports.portal_credential_verifier import (
    PortalCredentialVerifier,
)
from application.services.authentication_service import AuthenticationService
from application.services.batch_execution_service import BatchExecutionService
from application.services.batch_creation_service import BatchCreationService
from application.services.batch_portal_probe_service import (
    BatchPortalProbeService,
)
from application.services.portal_credential_service import (
    PortalCredentialService,
)
from application.services.user_management_service import UserManagementService
from domain.enums.user_role import UserRole
from domain.models.user_account import UserAccount
from infrastructure.config.settings import Settings
from infrastructure.security.jwt_service import (
    InvalidAccessTokenError,
    JWTService,
)
from infrastructure.security.scrypt_password_hasher import (
    ScryptPasswordHasher,
)


UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="La sesión no es válida o expiró.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_user_repository(request: Request) -> SQLiteUserRepository:
    return request.app.state.user_repository


def get_portal_credential_repository(
    request: Request,
) -> SQLitePortalCredentialRepository:
    return request.app.state.portal_credential_repository


def get_contract_file_validator(request: Request) -> ContractFileValidator:
    return request.app.state.contract_file_validator


def get_batch_repository(request: Request) -> SQLiteBatchRepository:
    return request.app.state.batch_repository


def get_batch_execution_service(request: Request) -> BatchExecutionService:
    return request.app.state.batch_execution_service


def get_batch_portal_probe_service(
    request: Request,
) -> BatchPortalProbeService:
    return request.app.state.batch_portal_probe_service


def get_batch_creation_service(
    validator: Annotated[
        ContractFileValidator,
        Depends(get_contract_file_validator),
    ],
    batches: Annotated[
        BatchRepository,
        Depends(get_batch_repository),
    ],
) -> BatchCreationService:
    return BatchCreationService(
        validations=validator,
        batches=batches,
    )


def get_password_hasher(request: Request) -> ScryptPasswordHasher:
    return request.app.state.password_hasher


def get_jwt_service(request: Request) -> JWTService:
    return request.app.state.jwt_service


def get_credential_cipher(request: Request) -> CredentialCipher:
    cipher = request.app.state.credential_cipher
    if cipher is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El cifrado de credenciales no está configurado. "
                "Defina RPA_FERNET_KEY en el archivo .env."
            ),
        )
    return cipher


def get_portal_credential_verifier(
    request: Request,
) -> PortalCredentialVerifier:
    return request.app.state.portal_credential_verifier


def get_authentication_service(
    users: Annotated[
        SQLiteUserRepository,
        Depends(get_user_repository),
    ],
    hasher: Annotated[
        ScryptPasswordHasher,
        Depends(get_password_hasher),
    ],
) -> AuthenticationService:
    return AuthenticationService(
        users=users,
        password_hasher=hasher,
    )


def get_user_management_service(
    users: Annotated[
        SQLiteUserRepository,
        Depends(get_user_repository),
    ],
    hasher: Annotated[
        ScryptPasswordHasher,
        Depends(get_password_hasher),
    ],
) -> UserManagementService:
    return UserManagementService(
        users=users,
        password_hasher=hasher,
    )


def get_portal_credential_service(
    repository: Annotated[
        SQLitePortalCredentialRepository,
        Depends(get_portal_credential_repository),
    ],
    cipher: Annotated[
        CredentialCipher,
        Depends(get_credential_cipher),
    ],
    verifier: Annotated[
        PortalCredentialVerifier,
        Depends(get_portal_credential_verifier),
    ],
) -> PortalCredentialService:
    return PortalCredentialService(
        repository=repository,
        cipher=cipher,
        verifier=verifier,
    )


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()


def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
    users: Annotated[
        SQLiteUserRepository,
        Depends(get_user_repository),
    ] = None,
    tokens: Annotated[JWTService, Depends(get_jwt_service)] = None,
) -> UserAccount:
    token = request.cookies.get(settings.auth_cookie_name)
    if token is None:
        token = _extract_bearer_token(authorization)
    if token is None:
        raise UNAUTHORIZED

    try:
        claims = tokens.decode_access_token(token)
    except InvalidAccessTokenError as error:
        raise UNAUTHORIZED from error

    user = users.find_by_id(claims.user_id)
    if user is None or not user.is_active:
        raise UNAUTHORIZED

    if user.username.casefold() != claims.username.casefold():
        raise UNAUTHORIZED

    return user


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


def require_roles(
    *allowed_roles: UserRole,
) -> Callable[[CurrentUser], UserAccount]:
    allowed = frozenset(allowed_roles)

    def dependency(user: CurrentUser) -> UserAccount:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta operación.",
            )
        return user

    return dependency


Superuser = Annotated[
    UserAccount,
    Depends(require_roles(UserRole.SUPERUSER)),
]
