from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr

from application.ports.portal_credential_verifier import (
    PortalCredentialVerificationResult,
)
from domain.enums.user_role import UserRole
from infrastructure.config.settings import Settings
from interfaces.api.main import create_app


class FakeVerifier:
    def __init__(self, *, success: bool = True) -> None:
        self.success = success

    def verify(self, *, portal_username: str, portal_password: str):
        assert portal_password
        return PortalCredentialVerificationResult(
            success=self.success,
            code="AUTHENTICATED" if self.success else "INVALID_CREDENTIALS",
            message=(
                "Las credenciales fueron validadas correctamente."
                if self.success
                else "Gestión Transparente rechazó las credenciales."
            ),
        )


def build_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_path=tmp_path / "api.sqlite3",
        jwt_secret_key=SecretStr(
            "test-secret-key-with-at-least-thirty-two-characters"
        ),
        fernet_key=SecretStr(Fernet.generate_key().decode("ascii")),
        cookie_secure=False,
        cors_origins=["http://testserver"],
    )


def create_account(app, *, username, dependency, role):
    return app.state.user_repository.create(
        username=username,
        password_hash=app.state.password_hasher.hash("Clave2026"),
        dependency=dependency,
        role=role,
    )


def login(client: TestClient, username: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Clave2026"},
    )
    assert response.status_code == 200


def test_superuser_should_save_and_test_credentials(tmp_path: Path) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(success=True),
    )

    with TestClient(app) as client:
        create_account(
            app,
            username="jefe",
            dependency="Adquisiciones",
            role=UserRole.SUPERUSER,
        )
        login(client, "jefe")

        initial = client.get("/api/v1/portal-credentials")
        assert initial.status_code == 200
        assert initial.json()["configured"] is False

        saved = client.put(
            "/api/v1/portal-credentials",
            json={
                "portal_username": "usuario.gt",
                "portal_password": "ClavePortal2026",
            },
        )
        assert saved.status_code == 200
        assert saved.json()["configured"] is True
        assert "portal_password" not in saved.json()
        assert "encrypted_password" not in saved.json()

        tested = client.post("/api/v1/portal-credentials/test")
        assert tested.status_code == 200
        assert tested.json()["success"] is True
        assert tested.json()["status"]["last_test_success"] is True


def test_operator_should_not_access_portal_credentials(
    tmp_path: Path,
) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(
            app,
            username="operador",
            dependency="Adquisiciones",
            role=UserRole.OPERATOR,
        )
        login(client, "operador")

        assert client.get("/api/v1/portal-credentials").status_code == 403
        assert client.put(
            "/api/v1/portal-credentials",
            json={
                "portal_username": "usuario.gt",
                "portal_password": "ClavePortal2026",
            },
        ).status_code == 403


def test_credentials_should_be_isolated_by_dependency(
    tmp_path: Path,
) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(
            app,
            username="jefe_adquisiciones",
            dependency="Adquisiciones",
            role=UserRole.SUPERUSER,
        )
        create_account(
            app,
            username="jefe_proyectos",
            dependency="Proyectos",
            role=UserRole.SUPERUSER,
        )

        login(client, "jefe_adquisiciones")
        client.put(
            "/api/v1/portal-credentials",
            json={
                "portal_username": "usuario.adquisiciones",
                "portal_password": "ClavePortal2026",
            },
        )
        client.post("/api/v1/auth/logout")

        login(client, "jefe_proyectos")
        status = client.get("/api/v1/portal-credentials")
        assert status.status_code == 200
        assert status.json()["configured"] is False
        assert status.json()["portal_username"] is None
