from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from adapters.dry_run_contract_executor import DryRunContractExecutor
from adapters.persistence.json_execution_evidence_repository import (
    JsonExecutionEvidenceRepository,
)
from adapters.persistence.sqlite import (
    SQLiteBatchRepository,
    SQLiteExecutionRepository,
    SQLitePortalCredentialRepository,
    SQLiteRealWriteAuthorizationRepository,
)
from application.services.batch_contract_execution_service import (
    BatchContractExecutionService,
)
from application.services.controlled_batch_contract_execution_service import (
    ControlledBatchContractExecutionService,
)
from application.services.real_write_authorization_service import (
    RealWriteAuthorizationService,
)
from application.use_cases.process_contract import ContractProcessingResult
from application.workflow import ExecutionCheckpointService
from domain.enums import (
    ContractStep,
    ContractorNature,
    ExecutionMode,
    ExecutionStatus,
)
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.errors.batch_contract_execution_errors import (
    BatchContractExecutionBlockedError,
    BatchContractExecutionConfirmationError,
)
from domain.models import (
    BudgetData,
    ContractData,
    ContractExecution,
    ContractorData,
    SupervisorData,
)
from domain.models.contract_batch import BatchContract, ContractBatch


class CompletingRealExecutor:
    def __init__(self, repository: SQLiteExecutionRepository) -> None:
        self._repository = repository
        self.calls: list[tuple[str, UUID | None]] = []

    def execute(
        self,
        *,
        contract: ContractData,
        execution_id: UUID | None = None,
    ) -> ContractProcessingResult:
        self.calls.append((contract.contract_number, execution_id))
        execution = ContractExecution.create(
            contract_number=contract.contract_number,
            dependency=contract.dependency,
        )
        now = datetime.now(UTC)
        execution.status = ExecutionStatus.COMPLETED
        execution.last_completed_step = ContractStep.COMPLETED
        execution.attempt_count = 1
        execution.started_at = now
        execution.updated_at = now
        execution.completed_at = now
        self._repository.save(execution)
        return ContractProcessingResult(
            execution=execution,
            transitions=(),
        )


def contract() -> ContractData:
    amount = Decimal("1476190")
    return ContractData(
        contract_number="70-2026",
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


def build_controlled_service(
    tmp_path: Path,
    *,
    real_write_enabled: bool,
    credentials_ready: bool,
):
    database = tmp_path / "controlled.sqlite3"
    batches = SQLiteBatchRepository(database)
    credentials = SQLitePortalCredentialRepository(database)
    executions = SQLiteExecutionRepository(database)
    batches.initialize()
    credentials.initialize()
    executions.initialize()

    if credentials_ready:
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

    now = datetime.now(UTC)
    stored = batches.create(
        ContractBatch(
            batch_id=uuid4(),
            validation_id=uuid4().hex,
            source_file_name="contratos.xlsx",
            dependency="Adquisiciones",
            created_by_user_id=1,
            created_by_username="jefe",
            status=BatchStatus.READY,
            contracts=(
                BatchContract(
                    item_id=uuid4(),
                    source_row_number=2,
                    contract=contract(),
                ),
            ),
            created_at=now,
            updated_at=now,
        )
    )

    real_executor = CompletingRealExecutor(executions)
    real_service = BatchContractExecutionService(
        batches=batches,
        credentials=credentials,
        checkpoints=ExecutionCheckpointService(executions),
        executor=real_executor,
        execution_enabled=real_write_enabled,
        reject_unit_test_values=True,
    )
    evidence = JsonExecutionEvidenceRepository(
        tmp_path / "execution_evidence"
    )
    evidence.initialize()
    authorization_repository = (
        SQLiteRealWriteAuthorizationRepository(database)
    )
    authorization_repository.initialize()
    authorization_service = RealWriteAuthorizationService(
        repository=authorization_repository,
        enabled=real_write_enabled,
        ttl_seconds=300,
    )
    controlled = ControlledBatchContractExecutionService(
        real_service=real_service,
        dry_run_executor=DryRunContractExecutor(),
        evidence=evidence,
        real_write_enabled=real_write_enabled,
        authorizations=authorization_service,
    )
    return stored, real_executor, evidence, controlled


def test_dry_run_is_default_safe_mode_and_persists_audit(
    tmp_path: Path,
) -> None:
    batch, real_executor, evidence, service = build_controlled_service(
        tmp_path,
        real_write_enabled=False,
        credentials_ready=False,
    )
    item = batch.contracts[0]

    preflight = service.preflight(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    assert preflight.mode is ExecutionMode.DRY_RUN
    assert preflight.can_execute is True
    assert preflight.required_confirmation == "SIMULAR CONTRATO 70-2026"
    assert preflight.real_write_enabled is False

    result = service.execute(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation="SIMULAR CONTRATO 70-2026",
        actor_username="jefe",
        actor_user_id=1,
    )

    assert result.mode is ExecutionMode.DRY_RUN
    assert result.writes_to_portal is False
    assert result.success is True
    assert result.batch.status is BatchStatus.READY
    assert result.item.status is BatchContractStatus.PENDING
    assert result.correlation_id is not None
    assert result.evidence_count == 11
    assert real_executor.calls == []

    stored = evidence.get(result.correlation_id)
    assert stored is not None
    assert stored.actor_username == "jefe"
    assert stored.mode is ExecutionMode.DRY_RUN
    assert stored.evidence_count == 11
    assert stored.events[-1].step is ContractStep.COMPLETED


def test_dry_run_status_returns_latest_audited_result(
    tmp_path: Path,
) -> None:
    batch, _, _, service = build_controlled_service(
        tmp_path,
        real_write_enabled=False,
        credentials_ready=False,
    )
    item = batch.contracts[0]

    executed = service.execute(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation="SIMULAR CONTRATO 70-2026",
        actor_username="jefe",
        actor_user_id=1,
    )
    status = service.status(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        mode=ExecutionMode.DRY_RUN,
    )

    assert status.correlation_id == executed.correlation_id
    assert status.success is True
    assert status.writes_to_portal is False
    assert status.last_completed_step is ContractStep.COMPLETED


def test_dry_run_requires_its_own_confirmation(
    tmp_path: Path,
) -> None:
    batch, _, _, service = build_controlled_service(
        tmp_path,
        real_write_enabled=False,
        credentials_ready=False,
    )
    item = batch.contracts[0]

    with pytest.raises(BatchContractExecutionConfirmationError):
        service.execute(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="EJECUTAR CONTRATO 70-2026",
            actor_username="jefe",
            actor_user_id=1,
        )


def test_real_write_is_blocked_without_institutional_authorization(
    tmp_path: Path,
) -> None:
    batch, real_executor, _, service = build_controlled_service(
        tmp_path,
        real_write_enabled=False,
        credentials_ready=True,
    )
    item = batch.contracts[0]

    preflight = service.preflight(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        mode=ExecutionMode.REAL,
    )

    assert preflight.can_execute is False
    assert "EXECUTION_DISABLED" in {
        issue.code for issue in preflight.issues
    }

    with pytest.raises(BatchContractExecutionBlockedError):
        service.execute(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="EJECUTAR CONTRATO 70-2026",
            actor_username="jefe",
            actor_user_id=1,
            mode=ExecutionMode.REAL,
        )

    assert real_executor.calls == []


def test_authorized_real_write_delegates_and_records_evidence(
    tmp_path: Path,
) -> None:
    batch, real_executor, evidence, service = build_controlled_service(
        tmp_path,
        real_write_enabled=True,
        credentials_ready=True,
    )
    item = batch.contracts[0]

    issued = service.issue_real_write_authorization(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation="AUTORIZAR ESCRITURA REAL 70-2026",
        actor_username="jefe",
        actor_user_id=1,
    )

    result = service.execute(
        batch_id=batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation="EJECUTAR CONTRATO 70-2026",
        actor_username="jefe",
        actor_user_id=1,
        mode=ExecutionMode.REAL,
        authorization_token=issued.token,
    )

    assert result.mode is ExecutionMode.REAL
    assert result.writes_to_portal is True
    assert result.success is True
    assert result.item.status is BatchContractStatus.COMPLETED
    assert real_executor.calls == [("70-2026", None)]
    assert result.correlation_id is not None
    assert result.authorization_id == issued.authorization.authorization_id
    assert result.authorization_consumed_at is not None

    stored = evidence.get(result.correlation_id)
    assert stored is not None
    assert stored.mode is ExecutionMode.REAL
    assert stored.actor_username == "jefe"
    assert stored.evidence_count == 2
    assert stored.events[0].outcome == "AUTHORIZATION_CONSUMED"
