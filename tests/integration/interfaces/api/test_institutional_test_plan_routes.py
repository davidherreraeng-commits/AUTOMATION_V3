from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.batch_portal_probe import BatchPortalProbeResult
from application.ports.portal_credential_verifier import (
    PortalCredentialVerificationResult,
)
from application.use_cases.process_contract import ContractProcessingResult
from domain.enums import ContractStep, ExecutionStatus
from domain.enums.user_role import UserRole
from domain.models import ContractData, ContractExecution
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
    def verify(self, *, portal_username, portal_password):
        return PortalCredentialVerificationResult(
            success=True,
            code="AUTHENTICATED",
            message="Credenciales correctas.",
        )


class FakeReadOnlyProbe:
    name = "fake-read-only-probe"

    def __init__(self) -> None:
        self.calls = 0

    def probe(self, *, portal_username, portal_password):
        self.calls += 1
        return BatchPortalProbeResult(
            success=True,
            code="PORTAL_READY",
            message="Acceso read-only confirmado.",
            authenticated=True,
            contracting_menu_found=True,
            enter_contract_found=True,
            assistant_access_found=True,
            duration_ms=250,
        )


class FakeContractExecutor:
    def execute(
        self,
        *,
        contract: ContractData,
        execution_id: UUID | None = None,
    ) -> ContractProcessingResult:
        execution = ContractExecution.create(
            contract_number=contract.contract_number,
            dependency=contract.dependency,
        )
        now = datetime.now(UTC)
        execution.status = ExecutionStatus.COMPLETED
        execution.last_completed_step = ContractStep.COMPLETED
        execution.updated_at = now
        execution.completed_at = now
        return ContractProcessingResult(
            execution=execution,
            transitions=(),
        )


def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_path=tmp_path / "api.sqlite3",
        upload_directory=tmp_path / "uploads",
        database_backup_directory=tmp_path / "backups",
        jwt_secret_key=SecretStr(
            "test-secret-key-with-at-least-thirty-two-characters"
        ),
        fernet_key=SecretStr(Fernet.generate_key().decode("ascii")),
        cors_origins=["http://testserver"],
        cookie_secure=False,
        batch_execution_enabled=True,
        institutional_test_plan_enabled=True,
    )


def workbook_bytes(*, test_values: bool = False) -> bytes:
    stream = BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)
    sheet.append(
        [
            "70-2026",
            "900469775-8",
            "I-23021-2026",
            "Servicio institucional.",
            "20/01/2026",
            "21/01/2026",
            "$ 1" if test_values else "$ 1.476.190",
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
            "$ 1" if test_values else "$ 1.476.190",
        ]
    )
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def prepare(
    client: TestClient,
    app,
    role=UserRole.SUPERUSER,
    *,
    test_values: bool = False,
):
    app.state.user_repository.create(
        username="jefe",
        password_hash=app.state.password_hasher.hash("Clave2026"),
        dependency="Adquisiciones",
        role=role,
    )
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "jefe", "password": "Clave2026"},
    ).status_code == 200
    if role is UserRole.SUPERUSER:
        assert client.put(
            "/api/v1/portal-credentials",
            json={
                "portal_username": "usuario.gt",
                "portal_password": "ClavePortal2026",
            },
        ).status_code == 200
        assert client.post(
            "/api/v1/portal-credentials/test"
        ).status_code == 200
    validated = client.post(
        "/api/v1/files/validate",
        files={
            "file": (
                "contratos.xlsx",
                workbook_bytes(test_values=test_values),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert validated.status_code == 200
    batch = client.post(
        "/api/v1/batches",
        json={
            "validation_id": validated.json()["validation_id"],
            "selected_row_numbers": [2],
        },
    )
    assert batch.status_code == 201
    payload = batch.json()
    item = payload["contracts"][0]
    endpoint = (
        f"/api/v1/batches/{payload['batch_id']}/contracts/"
        f"{item['item_id']}/execution/institutional-plan"
    )
    return payload, item, endpoint


def test_should_create_diagnose_arm_and_cancel_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("RPA_REAL_WRITE_AUTHORIZATION", raising=False)
    probe = FakeReadOnlyProbe()
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=probe,
        contract_executor=FakeContractExecutor(),
    )

    with TestClient(app) as client:
        batch, item, endpoint = prepare(client, app)

        initial = client.get(endpoint)
        assert initial.status_code == 200
        assert initial.json()["plan_id"] is None
        assert initial.json()["enabled"] is True

        created = client.post(
            endpoint,
            json={
                "confirmation": "CREAR PLAN INSTITUCIONAL 70-2026"
            },
        )
        assert created.status_code == 201
        plan_id = created.json()["plan_id"]
        assert created.json()["status"] == "DRAFT"

        diagnostic = client.post(
            f"{endpoint}/diagnostic",
            json={"plan_id": plan_id},
        )
        assert diagnostic.status_code == 200
        assert diagnostic.json()["status"] == "READY"
        assert diagnostic.json()["diagnostic_success"] is True
        assert probe.calls == 1

        armed = client.post(
            f"{endpoint}/arm",
            json={
                "plan_id": plan_id,
                "confirmation": (
                    "ARMAR PRUEBA INSTITUCIONAL 70-2026"
                ),
            },
        )
        assert armed.status_code == 200
        assert armed.json()["status"] == "ARMED"
        assert armed.json()["available"] is True

        execution_endpoint = (
            f"/api/v1/batches/{batch['batch_id']}/contracts/"
            f"{item['item_id']}/execution/preflight"
        )
        preflight = client.get(
            execution_endpoint,
            params={"mode": "REAL"},
        )
        assert preflight.status_code == 200
        assert preflight.json()["institutional_plan_id"] == plan_id
        assert preflight.json()["institutional_plan_ready"] is True
        assert preflight.json()["real_write_enabled"] is False

        cancelled = client.request(
            "DELETE",
            endpoint,
            json={
                "plan_id": plan_id,
                "confirmation": (
                    "CANCELAR PLAN INSTITUCIONAL 70-2026"
                ),
            },
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"
        assert {
            event["event_type"]
            for event in cancelled.json()["events"]
        } >= {"CREATED", "DIAGNOSTIC_PASSED", "ARMED", "CANCELLED"}


def test_operator_should_not_manage_institutional_plan(tmp_path: Path) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeReadOnlyProbe(),
        contract_executor=FakeContractExecutor(),
    )
    with TestClient(app) as client:
        _, _, endpoint = prepare(client, app, role=UserRole.OPERATOR)
        assert client.get(endpoint).status_code == 403
        assert client.post(
            endpoint,
            json={
                "confirmation": "CREAR PLAN INSTITUCIONAL 70-2026"
            },
        ).status_code == 403


def test_status_and_creation_should_allow_read_only_preparation_blockers(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        batch_portal_probe=FakeReadOnlyProbe(),
        contract_executor=FakeContractExecutor(),
    )

    with TestClient(app) as client:
        batch, item, endpoint = prepare(
            client,
            app,
            test_values=True,
        )
        app.state.portal_credential_repository.record_test_result(
            dependency="Adquisiciones",
            tested_at=datetime.now(UTC) - timedelta(hours=48),
            success=True,
            code="AUTHENTICATED",
        )

        status_response = client.get(endpoint)
        assert status_response.status_code == 200
        assert status_response.json()["plan_id"] is None

        created = client.post(
            endpoint,
            json={
                "confirmation": "CREAR PLAN INSTITUCIONAL 70-2026"
            },
        )
        assert created.status_code == 201
        assert created.json()["status"] == "DRAFT"

        diagnostic = client.post(
            f"{endpoint}/diagnostic",
            json={"plan_id": created.json()["plan_id"]},
        )
        assert diagnostic.status_code == 409
        assert diagnostic.json()["detail"]["code"] == (
            "INSTITUTIONAL_TEST_PLAN_DIAGNOSTIC_BLOCKED"
        )
        assert "credenciales expiró" in (
            diagnostic.json()["detail"]["message"]
        )
