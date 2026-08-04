from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from application.services.portal_credential_service import (
    PortalCredentialService,
)
from domain.errors.portal_credential_errors import (
    PortalCredentialEncryptionError,
    PortalCredentialsNotConfiguredError,
)
from interfaces.api.dependencies import (
    Superuser,
    get_portal_credential_service,
)
from interfaces.api.schemas.portal_credentials import (
    PortalCredentialStatusResponse,
    PortalCredentialTestResponse,
    SavePortalCredentialsRequest,
)


router = APIRouter(
    prefix="/portal-credentials",
    tags=["Credenciales de Gestión Transparente"],
)


@router.get("", response_model=PortalCredentialStatusResponse)
def get_status(
    actor: Superuser,
    service: Annotated[
        PortalCredentialService,
        Depends(get_portal_credential_service),
    ],
) -> PortalCredentialStatusResponse:
    return PortalCredentialStatusResponse.from_status(
        service.get_status(actor=actor)
    )


@router.put("", response_model=PortalCredentialStatusResponse)
def save_credentials(
    data: SavePortalCredentialsRequest,
    actor: Superuser,
    service: Annotated[
        PortalCredentialService,
        Depends(get_portal_credential_service),
    ],
) -> PortalCredentialStatusResponse:
    try:
        result = service.save(
            actor=actor,
            portal_username=data.portal_username,
            portal_password=data.portal_password,
        )
    except (ValueError, PortalCredentialEncryptionError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return PortalCredentialStatusResponse.from_status(result)


@router.post("/test", response_model=PortalCredentialTestResponse)
def test_saved_credentials(
    actor: Superuser,
    service: Annotated[
        PortalCredentialService,
        Depends(get_portal_credential_service),
    ],
) -> PortalCredentialTestResponse:
    try:
        outcome = service.test_saved(actor=actor)
    except PortalCredentialsNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except PortalCredentialEncryptionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    return PortalCredentialTestResponse.from_outcome(outcome)
