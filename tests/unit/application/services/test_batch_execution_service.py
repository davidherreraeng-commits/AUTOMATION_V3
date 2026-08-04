from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.batch_repository import SQLiteBatchRepository
from adapters.persistence.sqlite.portal_credential_repository import (
    SQLitePortalCredentialRepository,
)
from application.services.batch_execution_service import BatchExecutionService
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.enums.contractor_nature import ContractorNature
from domain.errors.batch_execution_errors import BatchExecutionBlockedError
from domain.models.budget import BudgetData
from domain.models.contract import ContractData
from domain.models.contract_batch import BatchContract, ContractBatch
from domain.models.contractor import ContractorData
from domain.models.supervisor import SupervisorData


class UnavailableRunner:
    name = "unavailable"
    available = False

    def run(self, *, batch, callbacks):
        raise AssertionError("No debe ejecutarse")


class SuccessRunner:
    name = "fake-success"
    available = True

    def run(self, *, batch, callbacks):
        for item in batch.contracts:
            callbacks.mark_contract_started(item.item_id)
            callbacks.mark_contract_finished(
                item.item_id,
                BatchContractStatus.COMPLETED,
                "Contrato simulado correctamente.",
            )


class FailureRunner:
    name = "fake-failure"
    available = True

    def run(self, *, batch, callbacks):
        callbacks.mark_contract_started(batch.contracts[0].item_id)
        raise RuntimeError("fallo controlado")


def contract(
    number: str,
    *,
    amount: Decimal = Decimal("1476190"),
) -> ContractData:
    return ContractData(
        contract_number=number,
        dependency="Adquisiciones",
        contractor=ContractorData(
            document_number="900469775-8",
            nature=ContractorNature.LEGAL_ENTITY,
        ),
        project_code="I-23021-2026",
        object_description="Servicio institucional.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=amount,
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="IDEA-2026",
            subsector="Tecnología",
            cdp_code="235097",
            gross_total=amount,
            budget_register_number="12026",
        ),
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Interno",
        ),
        secop_url="https://example.test/secop",
    )


def create_batch(
    repository: SQLiteBatchRepository,
    *,
    validation: str,
    amount: Decimal = Decimal("1476190"),
) -> ContractBatch:
    now = datetime.now(UTC)
    return repository.create(
        ContractBatch(
            batch_id=uuid4(),
            validation_id=validation,
            source_file_name="contratos.xlsx",
            dependency="Adquisiciones",
            created_by_user_id=1,
            created_by_username="jefe",
            status=BatchStatus.READY,
            contracts=(
                BatchContract(
                    item_id=uuid4(),
                    source_row_number=2,
                    contract=contract("70-2026", amount=amount),
                ),
            ),
            created_at=now,
            updated_at=now,
        )
    )


def repositories(tmp_path: Path):
    database = tmp_path / "rpa.sqlite3"
    batches = SQLiteBatchRepository(database)
    credentials = SQLitePortalCredentialRepository(database)
    batches.initialize()
    credentials.initialize()
    return batches, credentials


def configure_credentials(
    credentials: SQLitePortalCredentialRepository,
    *,
    tested_at: datetime | None = None,
    success: bool = True,
) -> None:
    credentials.upsert(
        dependency="Adquisiciones",
        portal_username="usuario.gt",
        encrypted_password="token-cifrado",
    )
    credentials.record_test_result(
        dependency="Adquisiciones",
        tested_at=tested_at or datetime.now(UTC),
        success=success,
        code="AUTHENTICATED" if success else "INVALID_CREDENTIALS",
    )


def wait_terminal(
    service: BatchExecutionService,
    batch_id,
    timeout: float = 3.0,
) -> ContractBatch:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = service.get(
            batch_id=batch_id,
            dependency="Adquisiciones",
        )
        if current.status in {
            BatchStatus.COMPLETED,
            BatchStatus.COMPLETED_WITH_ERRORS,
            BatchStatus.FAILED,
        }:
            return current
        time.sleep(0.02)
    raise AssertionError("El lote no alcanzó un estado terminal.")


def test_preflight_should_explain_all_blocking_conditions(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    stored = create_batch(
        batches,
        validation="a" * 32,
        amount=Decimal("1"),
    )
    service = BatchExecutionService(
        batches=batches,
        credentials=credentials,
        runner=UnavailableRunner(),
        execution_enabled=False,
        cipher_configured=False,
        reject_unit_test_values=True,
    )
    try:
        result = service.preflight(
            batch_id=stored.batch_id,
            dependency="Adquisiciones",
        )
        codes = {issue.code for issue in result.issues}
        assert result.can_execute is False
        assert {
            "EXECUTION_DISABLED",
            "RUNNER_UNAVAILABLE",
            "CREDENTIALS_NOT_CONFIGURED",
            "CIPHER_NOT_CONFIGURED",
            "TEST_VALUES_DETECTED",
        }.issubset(codes)
    finally:
        service.shutdown()


def test_preflight_should_accept_ready_batch_with_recent_credentials(
    tmp_path: Path,
) -> None:
    batches, credentials = repositories(tmp_path)
    stored = create_batch(batches, validation="b" * 32)
    configure_credentials(credentials)
    service = BatchExecutionService(
        batches=batches,
        credentials=credentials,
        runner=SuccessRunner(),
        execution_enabled=True,
        cipher_configured=True,
    )
    try:
        result = service.preflight(
            batch_id=stored.batch_id,
            dependency="Adquisiciones",
        )
        assert result.can_execute is True
        assert result.issues == ()
        assert result.credentials_recently_tested is True
    finally:
        service.shutdown()


def test_preflight_should_reject_expired_credentials(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    stored = create_batch(batches, validation="c" * 32)
    configure_credentials(
        credentials,
        tested_at=datetime.now(UTC) - timedelta(hours=25),
    )
    service = BatchExecutionService(
        batches=batches,
        credentials=credentials,
        runner=SuccessRunner(),
        execution_enabled=True,
        cipher_configured=True,
        credential_max_age_hours=24,
    )
    try:
        result = service.preflight(
            batch_id=stored.batch_id,
            dependency="Adquisiciones",
        )
        assert result.can_execute is False
        assert "CREDENTIALS_TEST_EXPIRED" in {
            issue.code for issue in result.issues
        }
    finally:
        service.shutdown()


def test_start_should_complete_batch_using_injected_runner(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    stored = create_batch(batches, validation="d" * 32)
    configure_credentials(credentials)
    service = BatchExecutionService(
        batches=batches,
        credentials=credentials,
        runner=SuccessRunner(),
        execution_enabled=True,
        cipher_configured=True,
    )
    try:
        claimed = service.start(
            batch_id=stored.batch_id,
            dependency="Adquisiciones",
        )
        assert claimed.status is BatchStatus.PROCESSING

        finished = wait_terminal(service, stored.batch_id)
        assert finished.status is BatchStatus.COMPLETED
        assert finished.contracts[0].status is BatchContractStatus.COMPLETED
        assert finished.contracts[0].last_message == (
            "Contrato simulado correctamente."
        )
    finally:
        service.shutdown()


def test_runner_failure_should_mark_batch_and_started_item_failed(
    tmp_path: Path,
) -> None:
    batches, credentials = repositories(tmp_path)
    stored = create_batch(batches, validation="e" * 32)
    configure_credentials(credentials)
    service = BatchExecutionService(
        batches=batches,
        credentials=credentials,
        runner=FailureRunner(),
        execution_enabled=True,
        cipher_configured=True,
    )
    try:
        service.start(
            batch_id=stored.batch_id,
            dependency="Adquisiciones",
        )
        finished = wait_terminal(service, stored.batch_id)
        assert finished.status is BatchStatus.FAILED
        assert finished.contracts[0].status is BatchContractStatus.FAILED
        assert "RuntimeError" in (finished.contracts[0].last_message or "")
    finally:
        service.shutdown()


def test_start_should_not_claim_batch_when_preflight_is_blocked(
    tmp_path: Path,
) -> None:
    batches, credentials = repositories(tmp_path)
    stored = create_batch(batches, validation="f" * 32)
    service = BatchExecutionService(
        batches=batches,
        credentials=credentials,
        runner=UnavailableRunner(),
        execution_enabled=False,
        cipher_configured=False,
    )
    try:
        with pytest.raises(BatchExecutionBlockedError):
            service.start(
                batch_id=stored.batch_id,
                dependency="Adquisiciones",
            )
        current = service.get(
            batch_id=stored.batch_id,
            dependency="Adquisiciones",
        )
        assert current.status is BatchStatus.READY
    finally:
        service.shutdown()
