from __future__ import annotations

from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.batch_portal_probe import (
    BatchAssistantProbeResult,
    BatchPortalProbeResult,
)
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


class FakeVerifier:
    def verify(self, *, portal_username: str, portal_password: str):
        return PortalCredentialVerificationResult(
            success=True,
            code="AUTHENTICATED",
            message="Credenciales correctas.",
        )


class FakePortalProbe:
    name = "fake-c1-c2-probe"

    def __init__(self) -> None:
        self.password: str | None = None

    def probe(self, *, portal_username: str, portal_password: str):
        return BatchPortalProbeResult(
            success=True,
            code="NAVIGATION_READY",
            message="Navegación disponible.",
        )

    def probe_assistant_form(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ):
        self.password = portal_password
        return BatchAssistantProbeResult(
            success=True,
            code="ASSISTANT_FORM_READY",
            message="Formulario C1-C2 disponible sin escritura.",
            authenticated=True,
            assistant_opened=True,
            assistant_container_found=True,
            record_type_found=True,
            contract_number_found=True,
            contractor_search_found=True,
            project_search_found=True,
            validate_button_found=True,
            duration_ms=1100,
        )


def settings(tmp_path: Path) -> Settings:
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
        batch_execution_enabled=False,
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


def workbook_bytes() -> bytes:
    stream = BytesIO()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Contratos"
    worksheet.append(HEADERS)
    worksheet.append(
        [
            "70-2026",
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


def test_superuser_should_probe_c1_c2_without_changing_batch(
    tmp_path: Path,
) -> None:
    probe = FakePortalProbe()
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=probe,
    )
    with TestClient(app) as client:
        create_account(app, username="jefe", role=UserRole.SUPERUSER)
        login(client, "jefe")
        save_and_test_credentials(client)
        batch = create_batch(client)

        response = client.post(
            f"/api/v1/batches/{batch['batch_id']}"
            "/execution/assistant-probe"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["code"] == "ASSISTANT_FORM_READY"
        assert payload["assistant_opened"] is True
        assert payload["validate_button_found"] is True
        assert payload["missing_controls"] == []
        assert "ClavePortal2026" not in response.text
        assert probe.password == "ClavePortal2026"

        current = client.get(f"/api/v1/batches/{batch['batch_id']}")
        assert current.status_code == 200
        assert current.json()["status"] == "READY"


def test_operator_should_not_probe_c1_c2(tmp_path: Path) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakePortalProbe(),
    )
    with TestClient(app) as client:
        create_account(app, username="operador", role=UserRole.OPERATOR)
        login(client, "operador")
        batch = create_batch(client)

        response = client.post(
            f"/api/v1/batches/{batch['batch_id']}"
            "/execution/assistant-probe"
        )

        assert response.status_code == 403


def test_cancelled_batch_should_reject_c1_c2_probe(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakePortalProbe(),
    )
    with TestClient(app) as client:
        create_account(app, username="jefe", role=UserRole.SUPERUSER)
        login(client, "jefe")
        save_and_test_credentials(client)
        batch = create_batch(client)
        cancelled = client.post(
            f"/api/v1/batches/{batch['batch_id']}/cancel"
        )
        assert cancelled.status_code == 200

        response = client.post(
            f"/api/v1/batches/{batch['batch_id']}"
            "/execution/assistant-probe"
        )

        assert response.status_code == 409
