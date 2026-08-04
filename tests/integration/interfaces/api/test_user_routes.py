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


def create_account(app, *, username, dependency, role, password="Clave2026"):
    return app.state.user_repository.create(
        username=username,
        password_hash=app.state.password_hasher.hash(password),
        dependency=dependency,
        role=role,
    )


def login(client: TestClient, username: str, password: str = "Clave2026"):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


def test_superuser_should_manage_users_from_own_dependency(
    tmp_path: Path,
) -> None:
    app = create_app(build_settings(tmp_path))

    with TestClient(app) as client:
        superuser = create_account(
            app,
            username="jefe",
            dependency="Adquisiciones",
            role=UserRole.SUPERUSER,
        )
        create_account(
            app,
            username="otro_area",
            dependency="Proyectos",
            role=UserRole.OPERATOR,
        )
        login(client, "jefe")

        created = client.post(
            "/api/v1/users",
            json={
                "username": "nuevo_operador",
                "temporary_password": "Temporal2026",
                "role": "OPERATOR",
            },
        )
        assert created.status_code == 201
        created_user = created.json()
        assert created_user["dependency"] == "Adquisiciones"
        assert created_user["must_change_password"] is True

        listed = client.get("/api/v1/users")
        assert listed.status_code == 200
        assert listed.json()["total"] == 2
        assert {item["username"] for item in listed.json()["items"]} == {
            "jefe",
            "nuevo_operador",
        }

        disabled = client.patch(
            f"/api/v1/users/{created_user['id']}/status",
            json={"is_active": False},
        )
        assert disabled.status_code == 200
        assert disabled.json()["is_active"] is False

        reset = client.post(
            f"/api/v1/users/{created_user['id']}/reset-password",
            json={"temporary_password": "NuevaTemporal2026"},
        )
        assert reset.status_code == 200
        assert reset.json()["must_change_password"] is True

        self_disable = client.patch(
            f"/api/v1/users/{superuser.user_id}/status",
            json={"is_active": False},
        )
        assert self_disable.status_code == 400


def test_operator_should_not_access_user_management(tmp_path: Path) -> None:
    app = create_app(build_settings(tmp_path))

    with TestClient(app) as client:
        create_account(
            app,
            username="operador",
            dependency="Adquisiciones",
            role=UserRole.OPERATOR,
        )
        login(client, "operador")

        listed = client.get("/api/v1/users")
        created = client.post(
            "/api/v1/users",
            json={
                "username": "otro",
                "temporary_password": "Temporal2026",
                "role": "OPERATOR",
            },
        )

        assert listed.status_code == 403
        assert created.status_code == 403


def test_should_not_manage_user_from_another_dependency(
    tmp_path: Path,
) -> None:
    app = create_app(build_settings(tmp_path))

    with TestClient(app) as client:
        create_account(
            app,
            username="jefe",
            dependency="Adquisiciones",
            role=UserRole.SUPERUSER,
        )
        other = create_account(
            app,
            username="usuario_proyectos",
            dependency="Proyectos",
            role=UserRole.OPERATOR,
        )
        login(client, "jefe")

        response = client.patch(
            f"/api/v1/users/{other.user_id}/status",
            json={"is_active": False},
        )

        assert response.status_code == 404
