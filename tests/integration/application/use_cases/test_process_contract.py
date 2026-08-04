from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.persistence.sqlite import SQLiteExecutionRepository
from application.dto import PortalStepVerification, PortalVerificationStatus
from application.use_cases.process_contract import (
    ContractExecutionIdentityMismatchError,
    ProcessContract,
)
from application.use_cases.resume_contract import ResumeContract
from application.workflow import ExecutionCheckpointService, StepExecutor
from domain.enums import (
    ContractStep,
    ContractorNature,
    ExecutionStatus,
)
from domain.errors import PortalTimeoutError
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


@dataclass
class FakeContractPortal:
    applied_steps: set[ContractStep] = field(default_factory=set)
    execute_calls: list[ContractStep] = field(default_factory=list)
    verify_calls: list[ContractStep] = field(default_factory=list)
    execute_errors: dict[ContractStep, list[Exception]] = field(
        default_factory=dict
    )
    recover_calls: int = 0

    def execute_step(self, step: ContractStep, contract: ContractData) -> None:
        self.execute_calls.append(step)
        errors = self.execute_errors.get(step)
        if errors:
            raise errors.pop(0)
        self.applied_steps.add(step)

    def verify_step(
        self,
        step: ContractStep,
        contract: ContractData,
    ) -> PortalStepVerification:
        self.verify_calls.append(step)
        status = (
            PortalVerificationStatus.CONFIRMED
            if step in self.applied_steps
            else PortalVerificationStatus.NOT_APPLIED
        )
        return PortalStepVerification(
            step=step,
            status=status,
            message=f"Verificación de {step.value}.",
        )

    def recover(self) -> None:
        self.recover_calls += 1


def build_contract(
    *,
    contract_number: str = "70-2026",
    dependency: str = "Proyectos Especiales",
) -> ContractData:
    return ContractData(
        contract_number=contract_number,
        dependency=dependency,
        contractor=ContractorData(
            document_number="900469775-8",
            nature=ContractorNature.LEGAL_ENTITY,
        ),
        project_code="I-23021-2026",
        object_description="Servicio institucional.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1476190"),
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="IDEA-2026",
            subsector="Tecnología",
            cdp_code="235097",
            gross_total=Decimal("1476190"),
        ),
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Supervisor",
        ),
    )


def create_environment(tmp_path: Path):
    repository = SQLiteExecutionRepository(tmp_path / "process-contract.db")
    checkpoints = ExecutionCheckpointService(repository)
    portal = FakeContractPortal()
    executor = StepExecutor(
        portal=portal,
        checkpoints=checkpoints,
        portal_profile="v2026_07",
    )
    processor = ProcessContract(
        executor=executor,
        checkpoints=checkpoints,
    )
    resumer = ResumeContract(
        processor=processor,
        checkpoints=checkpoints,
    )
    return repository, checkpoints, portal, processor, resumer


def test_should_process_contract_until_completed(tmp_path: Path) -> None:
    repository, _, portal, processor, _ = create_environment(tmp_path)
    contract = build_contract()

    result = processor.execute(contract)

    assert result.completed
    assert result.execution.status is ExecutionStatus.COMPLETED
    assert result.execution.last_completed_step is ContractStep.COMPLETED
    assert result.last_result is not None
    assert result.last_result.step is ContractStep.COMPLETED

    expected_portal_steps = {
        ContractStep.ASSISTANT_OPENED,
        ContractStep.HEADER_COMPLETED,
        ContractStep.HEADER_VALIDATED,
        ContractStep.GENERAL_DATA_COMPLETED,
        ContractStep.CONTRACT_SAVED,
        ContractStep.SUPERVISOR_LINKED,
        ContractStep.AVAILABILITY_LINKED,
        ContractStep.BUDGET_REGISTER_LINKED,
        ContractStep.ADDITIONAL_DATES_LINKED,
    }
    assert set(portal.execute_calls) == expected_portal_steps
    assert ContractStep.INPUT_VALIDATED not in portal.execute_calls

    stored = repository.get_by_id(result.execution.execution_id)
    assert stored is not None
    assert stored.status is ExecutionStatus.COMPLETED


def test_should_stop_at_retry_pending_and_resume_later(tmp_path: Path) -> None:
    _, _, portal, processor, resumer = create_environment(tmp_path)
    contract = build_contract()
    portal.execute_errors[ContractStep.ASSISTANT_OPENED] = [
        PortalTimeoutError("El portal no respondió.")
    ]

    interrupted = processor.execute(contract)

    assert interrupted.retry_pending
    assert interrupted.execution.last_failed_step is ContractStep.ASSISTANT_OPENED
    assert portal.recover_calls == 1

    resumed = resumer.execute(
        execution_id=interrupted.execution.execution_id,
        contract=contract,
    )

    assert resumed.completed
    assert resumed.execution.attempt_count == 2
    assert resumed.execution.status is ExecutionStatus.COMPLETED


def test_should_reject_checkpoint_from_another_contract(tmp_path: Path) -> None:
    _, checkpoints, _, processor, resumer = create_environment(tmp_path)
    original = build_contract()
    execution = checkpoints.create_or_get(
        contract_number=original.contract_number,
        dependency=original.dependency,
    )
    another_contract = build_contract(contract_number="71-2026")

    with pytest.raises(ContractExecutionIdentityMismatchError):
        resumer.execute(
            execution_id=execution.execution_id,
            contract=another_contract,
        )

    stored = checkpoints.get(execution.execution_id)
    assert stored.status is ExecutionStatus.PENDING
