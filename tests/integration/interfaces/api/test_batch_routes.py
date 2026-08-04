from __future__ import annotations

from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.portal_credential_verifier import (
    PortalCredentialVerificationResult,
)
from domain.enums.user_role import UserRole
from infrastructure.config.settings import Settings
from interfaces.api.main import create_app


HEADERS = [
    "No. de Contrato",
    "Cédula o Nit Contratista",
    "Código del Proyecto",
    "Objeto del Contrato",
    "Fecha de Suscripción",
    "Fecha de Inicio",
    "Valor",
    "Plazo Estimado (En Dias)",
    "Modalidad o Proceso",
    "Procedimiento/Causal",
    "Tipo de Contrato",
    "Rubro Presupuestal",
    "Sub-Sector",
    "Enlace Proceso SECOP II",
    "Cédula Supervisor",
    "No. CDP",
    "No. RP",
    "Total Bruto",
]


def valid_row(number: str) -> list:
    return [
        number,
        "900469775-8",
            "I-23021-2026",
        "Servicio de software institucional.",
        "20/01/2026",
        "21/01/2026",
        "$ 1.476.190",
        180,
        "Contratación Directa",
        "Prestación de Servicios",
        "Servicios",
        "IDEA-2026 - RECURSOS CONVENIO IDEA",
        "Tecnología",
        "https://community.secop.gov.co/example",
        "71693738",
        "235097",
        "950172",
        "$ 1.476.190",
    ]


class FakeVerifier:
    def verify(self, *, portal_username: str, portal_password: str):
        return PortalCredentialVerificationResult(
            success=True,
            code="AUTHENTICATED",
            message="Credenciales correctas.",
        )


def workbook_bytes(rows: list[list]) -> bytes:
    stream = BytesIO()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Contratos"
    worksheet.append(HEADERS)
    for row in rows:
        worksheet.append(row)
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def build_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_path=tmp_path / "api.sqlite3",
        upload_directory=tmp_path / "uploads",
        upload_max_bytes=10_000_000,
        default_budget_year=2026,
        jwt_secret_key=SecretStr(
            "test-secret-key-with-at-least-thirty-two-characters"
        ),
        fernet_key=SecretStr(Fernet.generate_key().decode("ascii")),
        cookie_secure=False,
        cors_origins=["http://testserver"],
    )


def create_account(app, *, username: str, dependency: str) -> None:
    app.state.user_repository.create(
        username=username,
        password_hash=app.state.password_hasher.hash("Clave2026"),
        dependency=dependency,
        role=UserRole.OPERATOR,
    )


def login(client: TestClient, username: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Clave2026"},
    )
    assert response.status_code == 200


def validate(client: TestClient, rows: list[list]) -> dict:
    response = client.post(
        "/api/v1/files/validate",
        files={
            "file": (
                "contratos.xlsx",
                workbook_bytes(rows),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def test_should_create_get_and_list_selected_contracts(tmp_path: Path) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(app, username="operador", dependency="Adquisiciones")
        login(client, "operador")
        validation = validate(
            client,
            [valid_row("70-2026"), valid_row("71-2026")],
        )

        created = client.post(
            "/api/v1/batches",
            json={
                "validation_id": validation["validation_id"],
                "selected_row_numbers": [3],
            },
        )

        assert created.status_code == 201
        payload = created.json()
        assert payload["dependency"] == "Adquisiciones"
        assert payload["status"] == "READY"
        assert payload["selected_count"] == 1
        assert payload["contracts"][0]["row_number"] == 3
        assert payload["contracts"][0]["contract_number"] == "71-2026"

        fetched = client.get(f"/api/v1/batches/{payload['batch_id']}")
        assert fetched.status_code == 200
        assert fetched.json() == payload

        listed = client.get("/api/v1/batches")
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["batch_id"] == payload["batch_id"]


def test_should_reject_rows_not_validated_as_processable(tmp_path: Path) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(app, username="operador", dependency="Adquisiciones")
        login(client, "operador")
        validation = validate(client, [valid_row("70-2026")])

        response = client.post(
            "/api/v1/batches",
            json={
                "validation_id": validation["validation_id"],
                "selected_row_numbers": [99],
            },
        )

        assert response.status_code == 400
        assert "Filas rechazadas: 99" in response.json()["detail"]


def test_should_reject_second_batch_from_same_validation(tmp_path: Path) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(app, username="operador", dependency="Adquisiciones")
        login(client, "operador")
        validation = validate(client, [valid_row("70-2026")])
        payload = {
            "validation_id": validation["validation_id"],
            "selected_row_numbers": [2],
        }

        assert client.post("/api/v1/batches", json=payload).status_code == 201
        duplicated = client.post("/api/v1/batches", json=payload)

        assert duplicated.status_code == 409


def test_should_isolate_validations_and_batches_by_dependency(
    tmp_path: Path,
) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(app, username="adquisiciones", dependency="Adquisiciones")
        create_account(app, username="proyectos", dependency="Proyectos")

        login(client, "adquisiciones")
        validation = validate(client, [valid_row("70-2026")])
        created = client.post(
            "/api/v1/batches",
            json={
                "validation_id": validation["validation_id"],
                "selected_row_numbers": [2],
            },
        )
        assert created.status_code == 201
        batch_id = created.json()["batch_id"]
        client.post("/api/v1/auth/logout")

        login(client, "proyectos")
        cross_validation = client.post(
            "/api/v1/batches",
            json={
                "validation_id": validation["validation_id"],
                "selected_row_numbers": [2],
            },
        )
        assert cross_validation.status_code == 404
        assert client.get(f"/api/v1/batches/{batch_id}").status_code == 404
        assert client.get("/api/v1/batches").json()["total"] == 0


def test_should_require_authenticated_session_for_batches(tmp_path: Path) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        assert client.get("/api/v1/batches").status_code == 401
        assert client.post(
            "/api/v1/batches",
            json={
                "validation_id": "a" * 32,
                "selected_row_numbers": [2],
            },
        ).status_code == 401
