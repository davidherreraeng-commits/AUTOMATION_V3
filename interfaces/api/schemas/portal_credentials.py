from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from application.services.portal_credential_service import (
    PortalCredentialStatus,
    PortalCredentialTestOutcome,
)


class SavePortalCredentialsRequest(BaseModel):
    portal_username: str = Field(min_length=1, max_length=160)
    portal_password: str = Field(min_length=1, max_length=256)

    @field_validator("portal_username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El usuario del portal es obligatorio.")
        return normalized


class PortalCredentialStatusResponse(BaseModel):
    dependency: str
    configured: bool
    portal_username: str | None
    updated_at: datetime | None
    last_tested_at: datetime | None
    last_test_success: bool | None
    last_test_code: str | None

    @classmethod
    def from_status(
        cls,
        status: PortalCredentialStatus,
    ) -> "PortalCredentialStatusResponse":
        return cls(
            dependency=status.dependency,
            configured=status.configured,
            portal_username=status.portal_username,
            updated_at=status.updated_at,
            last_tested_at=status.last_tested_at,
            last_test_success=status.last_test_success,
            last_test_code=status.last_test_code,
        )


class PortalCredentialTestResponse(BaseModel):
    success: bool
    code: str
    message: str
    tested_at: datetime
    status: PortalCredentialStatusResponse

    @classmethod
    def from_outcome(
        cls,
        outcome: PortalCredentialTestOutcome,
    ) -> "PortalCredentialTestResponse":
        return cls(
            success=outcome.success,
            code=outcome.code,
            message=outcome.message,
            tested_at=outcome.tested_at,
            status=PortalCredentialStatusResponse.from_status(
                outcome.status
            ),
        )
