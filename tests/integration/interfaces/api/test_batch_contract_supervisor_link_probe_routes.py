from __future__ import annotations

from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.batch_portal_probe import (
    BatchContractSupervisorLinkProbeResult,
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


class FakeProbe:
    name = "fake-contract-supervisor-link"

    def probe_contract_supervisor_link(self, *, contract, **kwargs):
        return BatchContractSupervisorLinkProbeResult(
            success=True,
            code="CONTRACT_SUPERVISOR_LINK_READY",
            message="Contrato y supervisor vinculados.",
            authenticated=True,
            assistant_opened=True,
            contract_saved_confirmed=True,
            supervisor_section_found=True,
            supervisor_dialog_opened=True,
            supervisor_nature_selected=True,
            supervisor_id_type_selected=True,
            supervisor_document_written=True,
            supervisor_result_found=True,
            supervisor_selected=True,
            supervisor_type_internal_confirmed=True,
            supervisor_validate_clicked=True,
            supervisor_validation_confirmed=True,
            supervisor_link_clicked=True,
            success_dialog_found=True,
            success_dialog_accepted=True,
            supervisor_linked_confirmed=True,
            availability_section_found=True,
            duration_ms=30000,
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
    worksheet.append([
        "81-2026",
        "1042063697",
        "I-23021-2026",
        "Contrato de prueba para supervisor.",
        "20/01/2026",
        "21/01/2026",
        "$ 1",
        30,
        "Contratación Directa",
        "Prestación de Servicios",
        "Servicios",
        "IDEA-2026",
        "Tecnología",
        "https://community.secop.gov.co/test",
        "71693738",
        "235097",
        "950172",
        "$ 1",
    ])
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
                (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
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
    assert client.put(
        "/api/v1/portal-credentials",
        json={
            "portal_username": "usuario.gt",
            "portal_password": "ClavePortal2026",
        },
    ).status_code == 200
    assert client.post("/api/v1/portal-credentials/test").status_code == 200


def test_superuser_should_save_and_link_internal_supervisor(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(app) as client:
        create_account(app, username="jefe", role=UserRole.SUPERUSER)
        login(client, "jefe")
        save_and_test_credentials(client)
        batch = create_batch(client)

        response = client.post(
            f"/api/v1/batches/{batch['batch_id']}"
            "/execution/contract-supervisor-link-probe",
            json={
                "item_id": batch["contracts"][0]["item_id"],
                "confirmation": "GUARDAR Y VINCULAR 81-2026",
                "allow_test_values": True,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == "CONTRACT_SUPERVISOR_LINK_READY"
        assert payload["supervisor_document"] == "71693738"
        assert payload["supervisor_type"] == "Interno"
        assert payload["contract_saved_confirmed"] is True
        assert payload["supervisor_linked_confirmed"] is True
        assert payload["availability_section_found"] is True


def test_should_reject_incorrect_supervisor_confirmation(tmp_path: Path) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(app) as client:
        create_account(app, username="jefe", role=UserRole.SUPERUSER)
        login(client, "jefe")
        save_and_test_credentials(client)
        batch = create_batch(client)

        response = client.post(
            f"/api/v1/batches/{batch['batch_id']}"
            "/execution/contract-supervisor-link-probe",
            json={
                "item_id": batch["contracts"][0]["item_id"],
                "confirmation": "GUARDAR 81-2026",
                "allow_test_values": True,
            },
        )

        assert response.status_code == 409


def test_operator_should_not_link_supervisor(tmp_path: Path) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(app) as client:
        create_account(app, username="operador", role=UserRole.OPERATOR)
        login(client, "operador")
        batch = create_batch(client)

        response = client.post(
            f"/api/v1/batches/{batch['batch_id']}"
            "/execution/contract-supervisor-link-probe",
            json={
                "item_id": batch["contracts"][0]["item_id"],
                "confirmation": "GUARDAR Y VINCULAR 81-2026",
                "allow_test_values": True,
            },
        )

        assert response.status_code == 403
