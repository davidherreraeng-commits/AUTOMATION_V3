from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from adapters.persistence.sqlite.portal_credential_repository import (
    SQLitePortalCredentialRepository,
)
from application.ports.portal_credential_verifier import (
    PortalCredentialVerificationResult,
)
from application.services.portal_credential_service import (
    PortalCredentialService,
)
from domain.enums.user_role import UserRole
from domain.errors.portal_credential_errors import (
    PortalCredentialPermissionError,
    PortalCredentialsNotConfiguredError,
)
from domain.models.user_account import UserAccount
from infrastructure.security.fernet_credential_cipher import (
    FernetCredentialCipher,
)


class FakeVerifier:
    def __init__(self, *, success: bool = True) -> None:
        self.success = success
        self.received = None

    def verify(self, *, portal_username: str, portal_password: str):
        self.received = (portal_username, portal_password)
        return PortalCredentialVerificationResult(
            success=self.success,
            code="AUTHENTICATED" if self.success else "INVALID_CREDENTIALS",
            message="Resultado de prueba",
        )


def actor(role: UserRole = UserRole.SUPERUSER) -> UserAccount:
    now = datetime.now(timezone.utc)
    return UserAccount(
        user_id=1,
        username="jefe",
        password_hash="hash-seguro",
        dependency="Adquisiciones",
        role=role,
        is_active=True,
        must_change_password=False,
        created_at=now,
        updated_at=now,
    )


def build_service(tmp_path: Path, verifier: FakeVerifier):
    repository = SQLitePortalCredentialRepository(tmp_path / "rpa.sqlite3")
    repository.initialize()
    cipher = FernetCredentialCipher(Fernet.generate_key().decode("ascii"))
    service = PortalCredentialService(
        repository=repository,
        cipher=cipher,
        verifier=verifier,
    )
    return service, repository


def test_should_save_encrypted_credentials_for_actor_dependency(
    tmp_path: Path,
) -> None:
    service, repository = build_service(tmp_path, FakeVerifier())

    status = service.save(
        actor=actor(),
        portal_username="usuario.gt",
        portal_password="ClavePortal2026",
    )
    stored = repository.find_by_dependency("Adquisiciones")

    assert status.configured is True
    assert status.portal_username == "usuario.gt"
    assert stored is not None
    assert stored.encrypted_password != "ClavePortal2026"


def test_should_decrypt_only_for_verification_and_record_result(
    tmp_path: Path,
) -> None:
    verifier = FakeVerifier(success=True)
    service, _ = build_service(tmp_path, verifier)
    service.save(
        actor=actor(),
        portal_username="usuario.gt",
        portal_password="ClavePortal2026",
    )

    outcome = service.test_saved(actor=actor())

    assert verifier.received == ("usuario.gt", "ClavePortal2026")
    assert outcome.success is True
    assert outcome.status.last_test_success is True
    assert outcome.status.last_test_code == "AUTHENTICATED"


def test_should_reject_test_when_credentials_are_not_configured(
    tmp_path: Path,
) -> None:
    service, _ = build_service(tmp_path, FakeVerifier())

    with pytest.raises(PortalCredentialsNotConfiguredError):
        service.test_saved(actor=actor())


def test_should_reject_operator_management(tmp_path: Path) -> None:
    service, _ = build_service(tmp_path, FakeVerifier())

    with pytest.raises(PortalCredentialPermissionError):
        service.get_status(actor=actor(UserRole.OPERATOR))
