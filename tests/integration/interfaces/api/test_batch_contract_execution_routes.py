from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

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
    def verify(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ) -> PortalCredentialVerificationResult:
        return PortalCredentialVerificationResult(
            success=True,
            code="AUTHENTICATED",
            message="Credenciales correctas.",
        )


class FakeContractExecutor:
    def __init__(self) -> None:
        self.repository = None
        self.calls: list[tuple[str, UUID | None]] = []

    def execute(
        self,
        *,
        contract: ContractData,
        execution_id: UUID | None = None,
    ) -> ContractProcessingResult:
        if self.repository is None:
            raise AssertionError("El repositorio no fue conectado a la prueba.")

        self.calls.append((contract.contract_number, execution_id))
        execution = (
            self.repository.get_by_id(execution_id)
            if execution_id is not None
            else self.repository.get_by_contract(
                contract.contract_number,
                contract.dependency,
            )
        )
        if execution is None:
            execution = ContractExecution.create(
                contract_number=contract.contract_number,
                dependency=contract.dependency,
            )

        now = datetime.now(UTC)
        execution.status = ExecutionStatus.COMPLETED
        execution.last_completed_step = ContractStep.COMPLETED
        execution.current_step = None
        execution.last_failed_step = None
        execution.last_error = None
        execution.attempt_count += 1
        execution.started_at = execution.started_at or now
        execution.updated_at = now
        execution.completed_at = now
        self.repository.save(execution)

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
        jwt_secret_key=SecretStr(
            "test-secret-key-with-at-least-thirty-two-characters"
        ),
        fernet_key=SecretStr(Fernet.generate_key().decode("ascii")),
        cookie_secure=False,
        cors_origins=["http://testserver"],
        batch_execution_enabled=True,
        batch_execution_reject_unit_test_values=True,
    )


def create_account(
    app,
    *,
    username: str,
    role: UserRole,
) -> None:
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


def test_superuser_should_execute_one_selected_contract(
    tmp_path: Path,
) -> None:
    executor = FakeContractExecutor()
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        contract_executor=executor,
    )

    with TestClient(app) as client:
        executor.repository = app.state.execution_repository
        create_account(app, username="jefe", role=UserRole.SUPERUSER)
        login(client, "jefe")
        save_and_test_credentials(client)
        batch = create_batch(client)
        item = batch["contracts"][0]
        endpoint = (
            f"/api/v1/batches/{batch['batch_id']}/contracts/"
            f"{item['item_id']}/execution"
        )

        preflight = client.get(f"{endpoint}/preflight")
        assert preflight.status_code == 200
        assert preflight.json()["can_execute"] is True
        required = preflight.json()["required_confirmation"]
        assert required == "EJECUTAR CONTRATO 70-2026"

        rejected = client.post(
            endpoint,
            json={"confirmation": "ACEPTO"},
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["code"] == (
            "WRITE_CONFIRMATION_REQUIRED"
        )
        assert executor.calls == []

        executed = client.post(
            endpoint,
            json={"confirmation": required},
        )
        assert executed.status_code == 200
        payload = executed.json()
        assert payload["success"] is True
        assert payload["item_status"] == "COMPLETED"
        assert payload["batch_status"] == "COMPLETED"
        assert payload["execution_status"] == "COMPLETED"
        assert payload["last_completed_step"] == "COMPLETED"
        assert executor.calls == [("70-2026", None)]

        status_response = client.get(endpoint)
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["execution_id"] == payload["execution_id"]
        assert status_payload["success"] is True


def test_operator_should_not_access_selected_contract_execution(
    tmp_path: Path,
) -> None:
    executor = FakeContractExecutor()
    app = create_app(
        settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
        contract_executor=executor,
    )

    with TestClient(app) as client:
        executor.repository = app.state.execution_repository
        create_account(app, username="operador", role=UserRole.OPERATOR)
        login(client, "operador")
        batch = create_batch(client)
        item = batch["contracts"][0]
        endpoint = (
            f"/api/v1/batches/{batch['batch_id']}/contracts/"
            f"{item['item_id']}/execution"
        )

        assert client.get(f"{endpoint}/preflight").status_code == 403
        assert client.get(endpoint).status_code == 403
        assert client.post(
            endpoint,
            json={"confirmation": "EJECUTAR CONTRATO 70-2026"},
        ).status_code == 403
