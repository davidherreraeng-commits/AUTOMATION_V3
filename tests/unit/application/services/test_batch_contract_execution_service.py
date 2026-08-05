from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from adapters.persistence.sqlite import (
    SQLiteBatchRepository,
    SQLiteExecutionRepository,
    SQLitePortalCredentialRepository,
)
from application.services.batch_contract_execution_service import (
    BatchContractExecutionService,
)
from application.use_cases.process_contract import ContractProcessingResult
from application.workflow import ExecutionCheckpointService
from domain.enums import ContractStep, ContractorNature, ExecutionStatus
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.errors.batch_contract_execution_errors import (
    BatchContractExecutionBlockedError,
    BatchContractExecutionConfirmationError,
    BatchContractExecutionIdentityError,
)
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)
from domain.models.contract_batch import BatchContract, ContractBatch


class SequenceExecutor:
    def __init__(
        self,
        *,
        repository: SQLiteExecutionRepository,
        statuses: list[ExecutionStatus],
    ) -> None:
        self._repository = repository
        self._statuses = list(statuses)
        self.calls: list[tuple[str, UUID | None]] = []

    def execute(
        self,
        *,
        contract: ContractData,
        execution_id: UUID | None = None,
    ) -> ContractProcessingResult:
        self.calls.append((contract.contract_number, execution_id))
        execution = (
            self._repository.get_by_id(execution_id)
            if execution_id is not None
            else self._repository.get_by_contract(
                contract.contract_number,
                contract.dependency,
            )
        )
        if execution is None:
            from domain.models import ContractExecution

            execution = ContractExecution.create(
                contract_number=contract.contract_number,
                dependency=contract.dependency,
            )

        status = self._statuses.pop(0)
        now = datetime.now(UTC)
        execution.attempt_count += 1
        execution.started_at = execution.started_at or now
        execution.updated_at = now
        execution.current_step = None
        execution.last_error = None

        if status is ExecutionStatus.COMPLETED:
            execution.status = ExecutionStatus.COMPLETED
            execution.last_completed_step = ContractStep.COMPLETED
            execution.last_failed_step = None
            execution.completed_at = now
        elif status is ExecutionStatus.RETRY_PENDING:
            execution.status = ExecutionStatus.RETRY_PENDING
            execution.last_completed_step = ContractStep.HEADER_VALIDATED
            execution.last_failed_step = ContractStep.GENERAL_DATA_COMPLETED
            execution.completed_at = None
        else:
            raise AssertionError(f"Estado no soportado por la prueba: {status}")

        self._repository.save(execution)
        return ContractProcessingResult(
            execution=execution,
            transitions=(),
        )


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
            budget_register_number="950172",
        ),
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Interno",
        ),
        secop_url="https://community.secop.gov.co/example",
    )


def create_batch(
    repository: SQLiteBatchRepository,
    *,
    count: int = 1,
    amount: Decimal = Decimal("1476190"),
) -> ContractBatch:
    now = datetime.now(UTC)
    items = tuple(
        BatchContract(
            item_id=uuid4(),
            source_row_number=index + 2,
            contract=contract(
                f"{70 + index}-2026",
                amount=amount,
            ),
        )
        for index in range(count)
    )
    return repository.create(
        ContractBatch(
            batch_id=uuid4(),
            validation_id=uuid4().hex,
            source_file_name="contratos.xlsx",
            dependency="Adquisiciones",
            created_by_user_id=1,
            created_by_username="jefe",
            status=BatchStatus.READY,
            contracts=items,
            created_at=now,
            updated_at=now,
        )
    )


def build_service(
    tmp_path: Path,
    *,
    statuses: list[ExecutionStatus],
    count: int = 1,
    amount: Decimal = Decimal("1476190"),
    allowed_nominal_value_contracts: tuple[str, ...] = (),
):
    database = tmp_path / "single-contract.sqlite3"
    batches = SQLiteBatchRepository(database)
    credentials = SQLitePortalCredentialRepository(database)
    executions = SQLiteExecutionRepository(database)
    batches.initialize()
    credentials.initialize()
    executions.initialize()

    credentials.upsert(
        dependency="Adquisiciones",
        portal_username="usuario.gt",
        encrypted_password="token-cifrado",
    )
    credentials.record_test_result(
        dependency="Adquisiciones",
        tested_at=datetime.now(UTC),
        success=True,
        code="AUTHENTICATED",
    )

    stored = create_batch(
        batches,
        count=count,
        amount=amount,
    )
    executor = SequenceExecutor(
        repository=executions,
        statuses=statuses,
    )
    service = BatchContractExecutionService(
        batches=batches,
        credentials=credentials,
        checkpoints=ExecutionCheckpointService(executions),
        executor=executor,
        execution_enabled=True,
        reject_unit_test_values=True,
        allowed_nominal_value_contracts=(
            allowed_nominal_value_contracts
        ),
    )
    return batches, executions, stored, executor, service


def test_preflight_should_require_exact_write_confirmation(
    tmp_path: Path,
) -> None:
    _, _, batch, executor, service = build_service(
        tmp_path,
        statuses=[ExecutionStatus.COMPLETED],
    )
    item = batch.contracts[0]

    preflight = service.preflight(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    assert preflight.can_execute is True
    assert preflight.required_confirmation == (
        "EJECUTAR CONTRATO 70-2026"
    )

    with pytest.raises(BatchContractExecutionConfirmationError):
        service.execute(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="ACEPTO",
        )

    assert executor.calls == []


def test_should_execute_only_selected_contract_and_keep_batch_open(
    tmp_path: Path,
) -> None:
    batches, _, batch, executor, service = build_service(
        tmp_path,
        statuses=[ExecutionStatus.COMPLETED],
        count=2,
    )
    selected = batch.contracts[0]

    result = service.execute(
        batch_id=batch.batch_id,
        item_id=selected.item_id,
        dependency="Adquisiciones",
        confirmation="EJECUTAR CONTRATO 70-2026",
    )

    assert result.success is True
    assert result.item.status is BatchContractStatus.COMPLETED
    assert result.batch.status is BatchStatus.PROCESSING
    assert result.batch.contracts[1].status is BatchContractStatus.PENDING
    assert executor.calls == [("70-2026", None)]

    stored = batches.get_by_id(
        batch.batch_id,
        dependency="Adquisiciones",
    )
    assert stored is not None
    assert stored.status is BatchStatus.PROCESSING


def test_should_finish_batch_when_selected_contract_is_last_pending_item(
    tmp_path: Path,
) -> None:
    _, _, batch, _, service = build_service(
        tmp_path,
        statuses=[ExecutionStatus.COMPLETED],
    )
    item = batch.contracts[0]

    result = service.execute(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation="EJECUTAR CONTRATO 70-2026",
    )

    assert result.batch.status is BatchStatus.COMPLETED
    assert result.item.status is BatchContractStatus.COMPLETED
    assert result.execution_status is ExecutionStatus.COMPLETED
    assert result.last_completed_step is ContractStep.COMPLETED


def test_should_resume_retry_pending_checkpoint_with_same_execution_id(
    tmp_path: Path,
) -> None:
    _, _, batch, executor, service = build_service(
        tmp_path,
        statuses=[
            ExecutionStatus.RETRY_PENDING,
            ExecutionStatus.COMPLETED,
        ],
    )
    item = batch.contracts[0]
    confirmation = "EJECUTAR CONTRATO 70-2026"

    interrupted = service.execute(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation=confirmation,
    )

    assert interrupted.retry_pending is True
    assert interrupted.item.status is BatchContractStatus.PROCESSING
    assert interrupted.execution_id is not None

    resumed = service.execute(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation=confirmation,
        execution_id=interrupted.execution_id,
    )

    assert resumed.success is True
    assert resumed.batch.status is BatchStatus.COMPLETED
    assert executor.calls[1] == (
        "70-2026",
        interrupted.execution_id,
    )


def test_should_reject_execution_id_from_another_contract(
    tmp_path: Path,
) -> None:
    _, _, batch, _, service = build_service(
        tmp_path,
        statuses=[ExecutionStatus.COMPLETED],
    )
    item = batch.contracts[0]

    with pytest.raises(BatchContractExecutionIdentityError):
        service.execute(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="EJECUTAR CONTRATO 70-2026",
            execution_id=uuid4(),
        )


def test_preflight_should_block_unit_test_values(
    tmp_path: Path,
) -> None:
    _, _, batch, _, service = build_service(
        tmp_path,
        statuses=[ExecutionStatus.COMPLETED],
        amount=Decimal("1"),
    )
    item = batch.contracts[0]

    preflight = service.preflight(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    assert preflight.can_execute is False
    assert "TEST_VALUES_DETECTED" in {
        issue.code for issue in preflight.issues
    }

    with pytest.raises(BatchContractExecutionBlockedError):
        service.execute(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="EJECUTAR CONTRATO 70-2026",
        )

def test_preflight_should_allow_explicit_institutional_nominal_value(
    tmp_path: Path,
) -> None:
    _, _, batch, _, service = build_service(
        tmp_path,
        statuses=[ExecutionStatus.COMPLETED],
        amount=Decimal("1"),
        allowed_nominal_value_contracts=(" 70-2026 ",),
    )
    item = batch.contracts[0]

    preflight = service.preflight(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    issues = {issue.code: issue for issue in preflight.issues}
    assert "TEST_VALUES_DETECTED" not in issues
    assert (
        issues["NOMINAL_VALUE_INSTITUTIONALLY_ALLOWED"].blocking
        is False
    )
    assert preflight.can_execute is True


def test_preflight_should_not_allow_partial_nominal_value_match(
    tmp_path: Path,
) -> None:
    _, _, batch, _, service = build_service(
        tmp_path,
        statuses=[ExecutionStatus.COMPLETED],
        amount=Decimal("1"),
        allowed_nominal_value_contracts=("70-202",),
    )
    item = batch.contracts[0]

    preflight = service.preflight(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    assert "TEST_VALUES_DETECTED" in {
        issue.code for issue in preflight.issues
    }
    assert preflight.can_execute is False

