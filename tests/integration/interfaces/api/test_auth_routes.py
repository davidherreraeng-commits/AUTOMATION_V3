from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr

from domain.enums.user_role import UserRole
from infrastructure.config.settings import Settings
from interfaces.api.main import create_app


def build_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_path=tmp_path / "api.sqlite3",
        jwt_secret_key=SecretStr(
            "test-secret-key-with-at-least-thirty-two-characters"
        ),
        cookie_secure=False,
        cors_origins=["http://testserver"],
    )


def test_login_me_and_logout(tmp_path: Path) -> None:
    app = create_app(build_settings(tmp_path))

    with TestClient(app) as client:
        repository = app.state.user_repository
        hasher = app.state.password_hasher
        repository.create(
            username="superusuario",
            password_hash=hasher.hash("ClaveSegura2026"),
            dependency="Adquisiciones",
            role=UserRole.SUPERUSER,
        )

        login = client.post(
            "/api/v1/auth/login",
            json={
                "username": "superusuario",
                "password": "ClaveSegura2026",
            },
        )

        assert login.status_code == 200
        assert login.json()["user"]["role"] == "SUPERUSER"
        assert login.json()["user"]["dependency"] == "Adquisiciones"
        assert "rpa_access_token" in client.cookies

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["username"] == "superusuario"

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 200

        after_logout = client.get("/api/v1/auth/me")
        assert after_logout.status_code == 401


def test_should_reject_invalid_credentials(tmp_path: Path) -> None:
    app = create_app(build_settings(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "desconocido",
                "password": "no-corresponde",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Usuario o contraseña incorrectos."
