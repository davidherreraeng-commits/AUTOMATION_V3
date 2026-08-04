from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from application.ports.credential_cipher import CredentialCipher
from application.ports.portal_credential_repository import (
    PortalCredentialRepository,
)
from application.ports.portal_credential_verifier import (
    PortalCredentialVerificationResult,
    PortalCredentialVerifier,
)
from domain.enums.user_role import UserRole
from domain.errors.portal_credential_errors import (
    PortalCredentialEncryptionError,
    PortalCredentialPermissionError,
    PortalCredentialsNotConfiguredError,
)
from domain.models.portal_credentials import PortalCredentials
from domain.models.user_account import UserAccount


@dataclass(frozen=True, slots=True)
class PortalCredentialStatus:
    dependency: str
    configured: bool
    portal_username: str | None
    updated_at: datetime | None
    last_tested_at: datetime | None
    last_test_success: bool | None
    last_test_code: str | None


@dataclass(frozen=True, slots=True)
class PortalCredentialTestOutcome:
    success: bool
    code: str
    message: str
    tested_at: datetime
    status: PortalCredentialStatus


class PortalCredentialService:
    """Administra credenciales GT aisladas por dependencia."""

    def __init__(
        self,
        *,
        repository: PortalCredentialRepository,
        cipher: CredentialCipher,
        verifier: PortalCredentialVerifier,
    ) -> None:
        self._repository = repository
        self._cipher = cipher
        self._verifier = verifier

    def get_status(self, *, actor: UserAccount) -> PortalCredentialStatus:
        self._require_superuser(actor)
        record = self._repository.find_by_dependency(actor.dependency)
        return self._to_status(actor.dependency, record)

    def save(
        self,
        *,
        actor: UserAccount,
        portal_username: str,
        portal_password: str,
    ) -> PortalCredentialStatus:
        self._require_superuser(actor)

        username = str(portal_username).strip()
        password = str(portal_password)

        if not username:
            raise ValueError("El usuario de Gestión Transparente es obligatorio.")
        if not password:
            raise ValueError(
                "La contraseña de Gestión Transparente es obligatoria."
            )

        try:
            encrypted = self._cipher.encrypt(password)
        except Exception as error:
            raise PortalCredentialEncryptionError(
                "No fue posible cifrar la contraseña del portal."
            ) from error

        record = self._repository.upsert(
            dependency=actor.dependency,
            portal_username=username,
            encrypted_password=encrypted,
        )
        return self._to_status(actor.dependency, record)

    def test_saved(
        self,
        *,
        actor: UserAccount,
    ) -> PortalCredentialTestOutcome:
        self._require_superuser(actor)

        record = self._repository.find_by_dependency(actor.dependency)
        if record is None:
            raise PortalCredentialsNotConfiguredError(actor.dependency)

        try:
            password = self._cipher.decrypt(record.encrypted_password)
        except Exception as error:
            raise PortalCredentialEncryptionError(
                "No fue posible descifrar las credenciales guardadas. "
                "Configure nuevamente el usuario y la contraseña."
            ) from error

        result = self._verifier.verify(
            portal_username=record.portal_username,
            portal_password=password,
        )
        tested_at = datetime.now(timezone.utc)

        updated = self._repository.record_test_result(
            dependency=actor.dependency,
            tested_at=tested_at,
            success=result.success,
            code=result.code,
        )

        return PortalCredentialTestOutcome(
            success=result.success,
            code=result.code,
            message=result.message,
            tested_at=tested_at,
            status=self._to_status(actor.dependency, updated),
        )

    @staticmethod
    def _require_superuser(actor: UserAccount) -> None:
        if actor.role is not UserRole.SUPERUSER:
            raise PortalCredentialPermissionError()

    @staticmethod
    def _to_status(
        dependency: str,
        record: PortalCredentials | None,
    ) -> PortalCredentialStatus:
        if record is None:
            return PortalCredentialStatus(
                dependency=dependency,
                configured=False,
                portal_username=None,
                updated_at=None,
                last_tested_at=None,
                last_test_success=None,
                last_test_code=None,
            )

        return PortalCredentialStatus(
            dependency=record.dependency,
            configured=True,
            portal_username=record.portal_username,
            updated_at=record.updated_at,
            last_tested_at=record.last_tested_at,
            last_test_success=record.last_test_success,
            last_test_code=record.last_test_code,
        )
