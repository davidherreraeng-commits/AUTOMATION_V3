from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.portal_credential_verifier import (
    PortalCredentialVerificationResult,
)
from domain.enums.batch_status import BatchContractStatus
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


class FakeVerifier:
    def verify(self, *, portal_username: str, portal_password: str):
        return PortalCredentialVerificationResult(
            success=True,
            code="AUTHENTICATED",
            message="Credenciales correctas.",
        )


class FakeRunner:
    name = "fake-api-runner"
    available = True

    def run(self, *, batch, callbacks):
        for item in batch.contracts:
            callbacks.mark_contract_started(item.item_id)
            callbacks.mark_contract_finished(
                item.item_id,
                BatchContractStatus.COMPLETED,
                "Procesado por runner de integración.",
            )


def settings(tmp_path: Path, *, enabled: bool = False) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_path=tmp_path / "api.sqlite3",
        upload_directory=tmp_path / "uploads",
        jwt_secret_key=SecretStr(
            "test-secret-key-with-at-least-thirty-two-characters"
        ),
        fernet_key=SecretStr(Fernet.generate_key().decode("ascii")),
        cookie_secure=False,
        cors_origins=["http://testserver"],
        batch_execution_enabled=enabled,
        batch_execution_reject_unit_test_values=True,
    )


def create_account(app, *, username: str, role: UserRole) -> None:
    app.state.user_repository.create(
        username=username,
        password_hash=app.state.password_hasher.hash("Clave2026"),
        dependency="Adquisiciones",
        role=role,
    )


def login(client: TestClient, username: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Clave2026"},
    )
    assert response.status_code == 200


def workbook_bytes(number: str = "70-2026") -> bytes:
    stream = BytesIO()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Contratos"
    worksheet.append(HEADERS)
    worksheet.append(
        [
            number,
            "900469775-8",
            "I-23021-2026",
            "Servicio institucional.",
            "20/01/2026",
            "21/01/2026",
            "$ 1.476.190",
            180,
            "Contratación Directa",
            "Prestación de Servicios",
            "Servicios",
            "IDEA-2026",
            "Tecnología",
            "https://community.secop.gov.co/example",
            "71693738",
            "235097",
            "950172",
            "$ 1.476.190",
        ]
    )
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def create_batch(client: TestClient) -> dict:
    validation = client.post(
        "/api/v1/files/validate",
        files={
            "file": (
                "contratos.xlsx",
                workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert validation.status_code == 200
    created = client.post(
        "/api/v1/batches",
        json={
            "validation_id": validation.json()["validation_id"],
            "selected_row_numbers": [2],
        },
    )
    assert created.status_code == 201
    return created.json()


def save_and_test_credentials(client: TestClient) -> None:
    saved = client.put(
        "/api/v1/portal-credentials",
        json={
            "portal_username": "usuario.gt",
            "portal_password": "ClavePortal2026",
        },
    )
    assert saved.status_code == 200
    tested = client.post("/api/v1/portal-credentials/test")
    assert tested.status_code == 200
    assert tested.json()["success"] is True


def test_superuser_should_receive_safe_blocking_preflight(tmp_path: Path) -> None:
    app = create_app(
        settings(tmp_path, enabled=False),
        portal_credential_verifier=FakeVerifier(),
    )
    with TestClient(app) as client:
        create_account(app, username="jefe", role=UserRole.SUPERUSER)
        login(client, "jefe")
        batch = create_batch(client)

        response = client.get(
            f"/api/v1/batches/{batch['batch_id']}/execution/preflight"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["can_execute"] is False
        codes = {issue["code"] for issue in payload["issues"]}
        assert "EXECUTION_DISABLED" in codes
        assert "RUNNER_UNAVAILABLE" in codes


def test_operator_should_not_access_execution_control(tmp_path: Path) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )
    with TestClient(app) as client:
        create_account(app, username="operador", role=UserRole.OPERATOR)
        login(client, "operador")
        batch = create_batch(client)

        assert client.get(
            f"/api/v1/batches/{batch['batch_id']}/execution/preflight"
        ).status_code == 403
        assert client.post(
            f"/api/v1/batches/{batch['batch_id']}/execution"
        ).status_code == 403


def test_enabled_execution_should_complete_using_injected_runner(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings(tmp_path, enabled=True),
        portal_credential_verifier=FakeVerifier(),
        batch_execution_runner=FakeRunner(),
    )
    with TestClient(app) as client:
        create_account(app, username="jefe", role=UserRole.SUPERUSER)
        login(client, "jefe")
        save_and_test_credentials(client)
        batch = create_batch(client)

        preflight = client.get(
            f"/api/v1/batches/{batch['batch_id']}/execution/preflight"
        )
        assert preflight.status_code == 200
        assert preflight.json()["can_execute"] is True

        started = client.post(
            f"/api/v1/batches/{batch['batch_id']}/execution"
        )
        assert started.status_code == 202
        assert started.json()["batch"]["status"] == "PROCESSING"

        deadline = time.monotonic() + 3
        payload = None
        while time.monotonic() < deadline:
            progress = client.get(
                f"/api/v1/batches/{batch['batch_id']}/execution"
            )
            assert progress.status_code == 200
            payload = progress.json()
            if payload["batch"]["status"] == "COMPLETED":
                break
            time.sleep(0.02)

        assert payload is not None
        assert payload["batch"]["status"] == "COMPLETED"
        assert payload["completed_count"] == 1
        assert payload["batch"]["contracts"][0]["last_message"] == (
            "Procesado por runner de integración."
        )


def test_superuser_should_cancel_ready_batch(tmp_path: Path) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )
    with TestClient(app) as client:
        create_account(app, username="jefe", role=UserRole.SUPERUSER)
        login(client, "jefe")
        batch = create_batch(client)

        cancelled = client.post(
            f"/api/v1/batches/{batch['batch_id']}/cancel"
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"

        repeated = client.post(
            f"/api/v1/batches/{batch['batch_id']}/cancel"
        )
        assert repeated.status_code == 409
