from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.batch_portal_probe import (
    BatchAssistantProbeResult,
    BatchHeaderDraftProbeResult,
    BatchGeneralDataDraftProbeResult,
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


class FakeProbe:
    name = "fake-header-validation"

    def __init__(self) -> None:
        self.contract_number: str | None = None

    def probe(self, **kwargs):
        return BatchPortalProbeResult(True, "READY", "Listo")

    def probe_assistant_form(self, **kwargs):
        return BatchAssistantProbeResult(True, "READY", "Listo")

    def probe_header_draft(self, **kwargs):
        return BatchHeaderDraftProbeResult(
            True,
            "HEADER_DRAFT_READY",
            "Listo",
        )

    def probe_general_data_draft(
        self,
        *,
        portal_username,
        portal_password,
        contract,
    ):
        self.contract_number = contract.contract_number
        return BatchGeneralDataDraftProbeResult(
            success=True,
            code="GENERAL_DATA_DRAFT_READY",
            message="C3 completo sin guardar.",
            authenticated=True,
            assistant_opened=True,
            header_validation_confirmed=True,
            object_written=True,
            signing_date_written=True,
            starting_date_written=True,
            amount_written=True,
            amount_in_words_generated=True,
            contract_term_written=True,
            term_unit_days_selected=True,
            process_type_selected=True,
            procedure_selected=True,
            contract_type_selected=True,
            other_currency_no_selected=True,
            general_data_completed=True,
            save_clicked=False,
            duration_ms=5000,
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
        "80-2026",
        "901398448-2",
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


def test_superuser_should_fill_general_data_without_saving(tmp_path: Path) -> None:
    probe = FakeProbe()
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
        item_id = batch["contracts"][0]["item_id"]

        response = client.post(
            f"/api/v1/batches/{batch['batch_id']}"
            "/execution/general-data-draft-probe",
            json={"item_id": item_id},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == "GENERAL_DATA_DRAFT_READY"
        assert payload["header_validation_confirmed"] is True
        assert payload["general_data_completed"] is True
        assert payload["amount_in_words_generated"] is True
        assert payload["general_validate_clicked"] is False
        assert payload["save_clicked"] is False
        assert probe.contract_number == "80-2026"

        current = client.get(f"/api/v1/batches/{batch['batch_id']}")
        assert current.json()["status"] == "READY"


def test_should_reject_general_data_for_contract_outside_batch(
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
            "/execution/general-data-draft-probe",
            json={"item_id": str(uuid4())},
        )

        assert response.status_code == 409


def test_operator_should_not_fill_general_data(tmp_path: Path) -> None:
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
            "/execution/general-data-draft-probe",
            json={"item_id": batch["contracts"][0]["item_id"]},
        )

        assert response.status_code == 403
