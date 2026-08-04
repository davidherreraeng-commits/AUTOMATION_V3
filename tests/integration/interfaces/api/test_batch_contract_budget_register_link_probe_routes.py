from __future__ import annotations

from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.batch_portal_probe import (
    BatchContractBudgetRegisterLinkProbeResult,
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
    "Fecha RP",
]


class FakeVerifier:
    def verify(self, **kwargs):
        return PortalCredentialVerificationResult(
            success=True,
            code="AUTHENTICATED",
            message="OK",
        )


class FakeProbe:
    name = "fake-budget-register"

    def probe_contract_budget_register_link(self, **kwargs):
        return BatchContractBudgetRegisterLinkProbeResult(
            success=True,
            code="CONTRACT_BUDGET_REGISTER_LINK_READY",
            message="Listo",
            authenticated=True,
            assistant_opened=True,
            contract_saved_confirmed=True,
            supervisor_linked_confirmed=True,
            availability_linked_row_confirmed=True,
            budget_register_section_found=True,
            budget_register_number_written=True,
            budget_register_date_provided=True,
            budget_register_date_written=True,
            budget_register_availability_selected=True,
            gross_total_written=True,
            budget_register_validate_clicked=True,
            budget_register_validation_confirmed=True,
            budget_register_link_clicked=True,
            budget_register_success_dialog_found=True,
            budget_register_success_dialog_accepted=True,
            budget_register_linked_confirmed=True,
            additional_dates_section_found=True,
        )


def settings(tmp_path):
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


def account(app, username, role):
    app.state.user_repository.create(
        username=username,
        password_hash=app.state.password_hasher.hash("Clave2026"),
        dependency="Adquisiciones",
        role=role,
    )


def login(client, username):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Clave2026"},
    )
    assert response.status_code == 200


def workbook_bytes():
    stream = BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Contratos"
    sheet.append(HEADERS)
    sheet.append(
        [
            "87-2026",
            "1042063697",
            "I-23021-2026",
            "Prueba",
            "20/01/2026",
            "21/01/2026",
            "$ 1",
            30,
            "Contratación Directa",
            "Prestación de Servicios",
            "Servicios",
            "2111340000101501",
            "Tecnología",
            "https://secop.test",
            "52263286",
            "704",
            "25",
            "$ 1",
            "03/08/2026",
        ]
    )
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def create_batch(client):
    validation = client.post(
        "/api/v1/files/validate",
        files={
            "file": (
                "c.xlsx",
                workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert validation.status_code == 200
    response = client.post(
        "/api/v1/batches",
        json={
            "validation_id": validation.json()["validation_id"],
            "selected_row_numbers": [2],
        },
    )
    assert response.status_code == 201
    return response.json()


def credentials(client):
    assert client.put(
        "/api/v1/portal-credentials",
        json={"portal_username": "u", "portal_password": "p"},
    ).status_code == 200
    assert client.post(
        "/api/v1/portal-credentials/test"
    ).status_code == 200


def test_superuser_should_link_budget_register(tmp_path: Path):
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(app) as client:
        account(app, "jefe", UserRole.SUPERUSER)
        login(client, "jefe")
        credentials(client)
        current_batch = create_batch(client)
        response = client.post(
            f"/api/v1/batches/{current_batch['batch_id']}"
            "/execution/contract-budget-register-link-probe",
            json={
                "item_id": current_batch["contracts"][0]["item_id"],
                "confirmation": "GUARDAR SUPERVISOR CDP Y RP 87-2026",
                "allow_test_values": True,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == "CONTRACT_BUDGET_REGISTER_LINK_READY"
        assert payload["cdp_code"] == "704"
        assert payload["budget_register_number"] == "25"
        assert payload["budget_register_date"] == "2026-08-03"
        assert payload["gross_total"] == "1"
        assert payload["additional_dates_section_found"] is True


def test_should_reject_wrong_confirmation(tmp_path: Path):
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(app) as client:
        account(app, "jefe", UserRole.SUPERUSER)
        login(client, "jefe")
        credentials(client)
        current_batch = create_batch(client)
        response = client.post(
            f"/api/v1/batches/{current_batch['batch_id']}"
            "/execution/contract-budget-register-link-probe",
            json={
                "item_id": current_batch["contracts"][0]["item_id"],
                "confirmation": "GUARDAR 87-2026",
                "allow_test_values": True,
            },
        )
        assert response.status_code == 409


def test_operator_should_not_link_budget_register(tmp_path: Path):
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeProbe(),
    )
    with TestClient(app) as client:
        account(app, "operador", UserRole.OPERATOR)
        login(client, "operador")
        current_batch = create_batch(client)
        response = client.post(
            f"/api/v1/batches/{current_batch['batch_id']}"
            "/execution/contract-budget-register-link-probe",
            json={
                "item_id": current_batch["contracts"][0]["item_id"],
                "confirmation": "GUARDAR SUPERVISOR CDP Y RP 87-2026",
                "allow_test_values": True,
            },
        )
        assert response.status_code == 403
