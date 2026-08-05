from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from adapters.persistence.sqlite.real_write_authorization_repository import (
    SQLiteRealWriteAuthorizationRepository,
)
from application.dto.real_write_authorization import RealWriteAuthorization
from domain.enums import RealWriteAuthorizationStatus
from domain.enums.user_role import UserRole
from infrastructure.config.settings import Settings
from interfaces.api.main import create_app


class FakeVerifier:
    pass


class FakeProbe:
    pass


def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_path=tmp_path / "data" / "rpa.sqlite3",
        database_backup_directory=tmp_path / "database_backups",
        jwt_secret_key=SecretStr(
            "test-secret-key-with-at-least-thirty-two-characters"
        ),
        cookie_secure=False,
        cors_origins=["http://testserver"],
    )


def test_app_startup_should_create_and_report_runtime_database(
    tmp_path: Path,
) -> None:
    configured = settings(tmp_path)
    app = create_app(
        configured,
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )

    assert not configured.resolved_database_path.exists()

    with TestClient(app) as client:
        response = client.get("/health")
        report = app.state.database_bootstrap_report

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert report.created_database is True
        assert report.migration_applied is True
        assert app.state.user_repository.database_path == (
            configured.resolved_database_path
        )

    with sqlite3.connect(configured.resolved_database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "users" in tables
    assert "contract_batches" in tables
    assert "contract_executions" in tables
    assert "real_write_authorizations" in tables
    assert "rpa_schema_migrations" in tables


def test_app_restart_should_preserve_local_user_data(
    tmp_path: Path,
) -> None:
    configured = settings(tmp_path)
    first_app = create_app(
        configured,
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )

    with TestClient(first_app):
        first_app.state.user_repository.create(
            username="jefe",
            password_hash="hash-seguro",
            dependency="Adquisiciones",
            role=UserRole.SUPERUSER,
        )

    second_app = create_app(
        configured,
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(second_app):
        restored = second_app.state.user_repository.find_by_username(
            "jefe"
        )
        report = second_app.state.database_bootstrap_report

    assert restored is not None
    assert restored.dependency == "Adquisiciones"
    assert report.created_database is False
    assert report.migration_applied is False
    assert report.backup_path is None

def test_app_startup_should_sweep_expired_authorizations(
    tmp_path: Path,
) -> None:
    configured = settings(tmp_path)
    first_app = create_app(
        configured,
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(first_app):
        pass

    repository = SQLiteRealWriteAuthorizationRepository(
        configured.resolved_database_path
    )
    repository.initialize()
    now = datetime.now(UTC)
    batch_id = uuid4()
    item_id = uuid4()
    issued = repository.issue(
        RealWriteAuthorization(
            authorization_id=uuid4(),
            token_hash="e" * 64,
            batch_id=batch_id,
            item_id=item_id,
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            status=RealWriteAuthorizationStatus.ACTIVE,
            issued_at=now - timedelta(minutes=2),
            expires_at=now - timedelta(minutes=1),
        )
    )

    second_app = create_app(
        configured,
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(second_app):
        assert second_app.state.expired_real_write_authorizations == 1
        latest = second_app.state.real_write_authorization_repository.get_latest(
            batch_id=batch_id,
            item_id=item_id,
            actor_username="jefe",
            actor_user_id=1,
            now=now,
        )

    assert latest is not None
    assert latest.authorization_id == issued.authorization_id
    assert latest.status is RealWriteAuthorizationStatus.EXPIRED

