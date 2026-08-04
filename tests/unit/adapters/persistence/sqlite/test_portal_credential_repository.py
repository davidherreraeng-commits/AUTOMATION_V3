from datetime import datetime, timezone
from pathlib import Path

from adapters.persistence.sqlite.portal_credential_repository import (
    SQLitePortalCredentialRepository,
)


def test_should_upsert_and_find_credentials_case_insensitively(
    tmp_path: Path,
) -> None:
    repository = SQLitePortalCredentialRepository(tmp_path / "rpa.sqlite3")
    repository.initialize()

    created = repository.upsert(
        dependency="Adquisiciones",
        portal_username="usuario.gt",
        encrypted_password="token-cifrado",
    )
    loaded = repository.find_by_dependency("ADQUISICIONES")

    assert loaded is not None
    assert loaded.dependency == "Adquisiciones"
    assert loaded.portal_username == "usuario.gt"
    assert loaded.encrypted_password == "token-cifrado"
    assert created.last_test_success is None


def test_should_record_test_and_reset_it_after_credentials_change(
    tmp_path: Path,
) -> None:
    repository = SQLitePortalCredentialRepository(tmp_path / "rpa.sqlite3")
    repository.initialize()
    repository.upsert(
        dependency="Adquisiciones",
        portal_username="usuario.gt",
        encrypted_password="token-1",
    )

    tested = repository.record_test_result(
        dependency="Adquisiciones",
        tested_at=datetime.now(timezone.utc),
        success=True,
        code="AUTHENTICATED",
    )
    assert tested.last_test_success is True
    assert tested.last_test_code == "AUTHENTICATED"

    updated = repository.upsert(
        dependency="Adquisiciones",
        portal_username="usuario.nuevo",
        encrypted_password="token-2",
    )
    assert updated.portal_username == "usuario.nuevo"
    assert updated.last_tested_at is None
    assert updated.last_test_success is None
    assert updated.last_test_code is None
