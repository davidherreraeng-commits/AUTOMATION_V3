from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from adapters.persistence.sqlite import (
    SQLiteExecutionRepository,
)
from application.dto import (
    PortalStepVerification,
    PortalVerificationStatus,
    StepExecutionOutcome,
)
from application.workflow import (
    ExecutionCheckpointService,
    StepExecutor,
)
from domain.enums import (
    ContractStep,
    ContractorNature,
    ExecutionStatus,
)
from domain.errors import (
    PortalAlreadyExistsError,
    PortalStructureChangedError,
    PortalTimeoutError,
    PortalValidationError,
)
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


@dataclass
class FakeContractPortal:
    """
    Implementación simulada del puerto ContractPortal.

    Permite controlar:

    - Etapas aplicadas.
    - Invocaciones de ejecución.
    - Invocaciones de verificación.
    - Errores producidos por cada etapa.
    - Secuencias de resultados de verificación.
    - Intentos de recuperación.
    """

    applied_steps: set[ContractStep] = field(
        default_factory=set
    )

    execute_calls: list[ContractStep] = field(
        default_factory=list
    )

    verify_calls: list[ContractStep] = field(
        default_factory=list
    )

    execute_errors: dict[
        ContractStep,
        Exception,
    ] = field(
        default_factory=dict
    )

    verification_sequences: dict[
        ContractStep,
        list[PortalVerificationStatus],
    ] = field(
        default_factory=dict
    )

    recover_calls: int = 0

    def execute_step(
        self,
        step: ContractStep,
        contract: ContractData,
    ) -> None:
        self.execute_calls.append(step)

        error = self.execute_errors.get(step)

        if error is not None:
            raise error

        self.applied_steps.add(step)

    def verify_step(
        self,
        step: ContractStep,
        contract: ContractData,
    ) -> PortalStepVerification:
        self.verify_calls.append(step)

        sequence = self.verification_sequences.get(
            step
        )

        if sequence:
            status = sequence.pop(0)

        elif step in self.applied_steps:
            status = PortalVerificationStatus.CONFIRMED

        else:
            status = PortalVerificationStatus.NOT_APPLIED

        return PortalStepVerification(
            step=step,
            status=status,
            message=f"Verificación de {step.value}.",
        )

    def recover(self) -> None:
        self.recover_calls += 1


def build_contract() -> ContractData:
    """
    Construye un contrato válido para las pruebas del ejecutor.
    """

    contractor = ContractorData(
        document_number="900469775-8",
        nature=ContractorNature.LEGAL_ENTITY,
    )

    supervisor = SupervisorData(
        document_number="71693738",
        supervisor_type="Supervisor",
    )

    budget = BudgetData(
        year=2026,
        item="IDEA-2026",
        subsector="Tecnología",
        cdp_code="235097",
        gross_total=Decimal("1476190"),
    )

    return ContractData(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
        contractor=contractor,
        project_code="I-23021-2026",
        object_description=(
            "Servicio institucional para la administración "
            "del sistema."
        ),
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1476190"),
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=budget,
        supervisor=supervisor,
    )


def create_environment(
    tmp_path: Path,
) -> tuple[
    StepExecutor,
    ExecutionCheckpointService,
    SQLiteExecutionRepository,
    FakeContractPortal,
    ContractData,
    object,
]:
    """
    Crea el entorno completo de integración:

    StepExecutor
        → ExecutionCheckpointService
        → SQLiteExecutionRepository
        → FakeContractPortal
    """

    repository = SQLiteExecutionRepository(
        tmp_path / "step_executor.db"
    )

    checkpoints = ExecutionCheckpointService(
        repository
    )

    portal = FakeContractPortal()

    executor = StepExecutor(
        portal=portal,
        checkpoints=checkpoints,
        portal_profile="v2026_07",
    )

    contract = build_contract()

    execution = checkpoints.create_or_get(
        contract_number=contract.contract_number,
        dependency=contract.dependency,
    )

    return (
        executor,
        checkpoints,
        repository,
        portal,
        contract,
        execution,
    )


def advance_input_validation(
    executor: StepExecutor,
    contract: ContractData,
    execution_id: UUID,
) -> None:
    """
    Confirma INPUT_VALIDATED para dejar preparada la primera etapa
    que sí necesita interacción con el portal.
    """

    result = executor.execute_next(
        execution_id=execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.STEP_CONFIRMED
    )

    assert (
        result.step
        is ContractStep.INPUT_VALIDATED
    )


def test_should_confirm_input_without_using_portal(
    tmp_path: Path,
) -> None:
    (
        executor,
        _,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.STEP_CONFIRMED
    )

    assert (
        result.step
        is ContractStep.INPUT_VALIDATED
    )

    assert portal.execute_calls == []
    assert portal.verify_calls == []

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None
    assert stored.status is ExecutionStatus.RUNNING

    assert (
        stored.last_completed_step
        is ContractStep.INPUT_VALIDATED
    )

    assert stored.current_step is None
    assert stored.attempt_count == 1
    assert stored.portal_profile == "v2026_07"


def test_should_execute_and_confirm_portal_step(
    tmp_path: Path,
) -> None:
    (
        executor,
        _,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    advance_input_validation(
        executor,
        contract,
        execution.execution_id,
    )

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.STEP_CONFIRMED
    )

    assert (
        result.step
        is ContractStep.ASSISTANT_OPENED
    )

    assert portal.execute_calls == [
        ContractStep.ASSISTANT_OPENED,
    ]

    assert portal.verify_calls == [
        ContractStep.ASSISTANT_OPENED,
    ]

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None

    assert (
        stored.last_completed_step
        is ContractStep.ASSISTANT_OPENED
    )

    assert stored.current_step is None


def test_should_reconcile_confirmed_open_step_without_reexecuting(
    tmp_path: Path,
) -> None:
    (
        executor,
        checkpoints,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    advance_input_validation(
        executor,
        contract,
        execution.execution_id,
    )

    opened = checkpoints.begin_next_step(
        execution.execution_id
    )

    assert (
        opened.current_step
        is ContractStep.ASSISTANT_OPENED
    )

    portal.applied_steps.add(
        ContractStep.ASSISTANT_OPENED
    )

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.STEP_RECONCILED
    )

    assert (
        result.step
        is ContractStep.ASSISTANT_OPENED
    )

    assert portal.execute_calls == []

    assert portal.verify_calls == [
        ContractStep.ASSISTANT_OPENED,
    ]

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None
    assert stored.current_step is None

    assert (
        stored.last_completed_step
        is ContractStep.ASSISTANT_OPENED
    )


def test_should_execute_open_step_when_verification_says_not_applied(
    tmp_path: Path,
) -> None:
    (
        executor,
        checkpoints,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    advance_input_validation(
        executor,
        contract,
        execution.execution_id,
    )

    checkpoints.begin_next_step(
        execution.execution_id
    )

    portal.verification_sequences[
        ContractStep.ASSISTANT_OPENED
    ] = [
        PortalVerificationStatus.NOT_APPLIED,
    ]

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.STEP_CONFIRMED
    )

    assert (
        result.step
        is ContractStep.ASSISTANT_OPENED
    )

    assert portal.execute_calls == [
        ContractStep.ASSISTANT_OPENED,
    ]

    # Primera verificación: reconciliación.
    # Segunda verificación: postcondición después de ejecutar.
    assert portal.verify_calls == [
        ContractStep.ASSISTANT_OPENED,
        ContractStep.ASSISTANT_OPENED,
    ]

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None
    assert stored.current_step is None

    assert (
        stored.last_completed_step
        is ContractStep.ASSISTANT_OPENED
    )


def test_should_send_ambiguous_state_to_manual_review(
    tmp_path: Path,
) -> None:
    (
        executor,
        checkpoints,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    advance_input_validation(
        executor,
        contract,
        execution.execution_id,
    )

    checkpoints.begin_next_step(
        execution.execution_id
    )

    portal.verification_sequences[
        ContractStep.ASSISTANT_OPENED
    ] = [
        PortalVerificationStatus.AMBIGUOUS,
    ]

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.MANUAL_REVIEW
    )

    assert (
        result.execution.status
        is ExecutionStatus.MANUAL_REVIEW
    )

    assert portal.execute_calls == []

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None

    assert (
        stored.status
        is ExecutionStatus.MANUAL_REVIEW
    )

    assert stored.last_error is not None

    assert (
        stored.last_error.code
        == "AMBIGUOUS_PORTAL_STEP_STATE"
    )


def test_should_mark_retry_pending_for_timeout(
    tmp_path: Path,
) -> None:
    (
        executor,
        _,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    advance_input_validation(
        executor,
        contract,
        execution.execution_id,
    )

    portal.execute_errors[
        ContractStep.ASSISTANT_OPENED
    ] = PortalTimeoutError(
        "El portal no respondió."
    )

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.RETRY_PENDING
    )

    assert (
        result.execution.status
        is ExecutionStatus.RETRY_PENDING
    )

    assert (
        result.execution.last_failed_step
        is ContractStep.ASSISTANT_OPENED
    )

    assert result.execution.last_error is not None

    assert (
        result.execution.last_error.code
        == "PORTAL_TIMEOUT"
    )

    assert result.execution.last_error.retryable
    assert portal.recover_calls == 1

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None

    assert (
        stored.status
        is ExecutionStatus.RETRY_PENDING
    )


def test_should_fail_for_non_retryable_validation_error(
    tmp_path: Path,
) -> None:
    (
        executor,
        _,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    advance_input_validation(
        executor,
        contract,
        execution.execution_id,
    )

    portal.execute_errors[
        ContractStep.ASSISTANT_OPENED
    ] = PortalValidationError(
        "El portal rechazó los datos."
    )

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.FAILED
    )

    assert (
        result.execution.status
        is ExecutionStatus.FAILED
    )

    assert result.execution.last_error is not None

    assert (
        result.execution.last_error.code
        == "PORTAL_VALIDATION_ERROR"
    )

    assert not result.execution.last_error.retryable
    assert portal.recover_calls == 1

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None
    assert stored.status is ExecutionStatus.FAILED


def test_should_send_structure_change_to_manual_review(
    tmp_path: Path,
) -> None:
    (
        executor,
        _,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    advance_input_validation(
        executor,
        contract,
        execution.execution_id,
    )

    portal.execute_errors[
        ContractStep.ASSISTANT_OPENED
    ] = PortalStructureChangedError(
        "La estructura del portal cambió."
    )

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.MANUAL_REVIEW
    )

    assert (
        result.execution.status
        is ExecutionStatus.MANUAL_REVIEW
    )

    assert result.execution.last_error is not None

    assert (
        result.execution.last_error.code
        == "PORTAL_STRUCTURE_CHANGED"
    )

    assert portal.recover_calls == 1

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None

    assert (
        stored.status
        is ExecutionStatus.MANUAL_REVIEW
    )


def test_should_mark_contract_as_already_existing(
    tmp_path: Path,
) -> None:
    (
        executor,
        _,
        repository,
        portal,
        contract,
        execution,
    ) = create_environment(tmp_path)

    advance_input_validation(
        executor,
        contract,
        execution.execution_id,
    )

    portal.execute_errors[
        ContractStep.ASSISTANT_OPENED
    ] = PortalAlreadyExistsError(
        "El contrato ya está registrado."
    )

    result = executor.execute_next(
        execution_id=execution.execution_id,
        contract=contract,
    )

    assert (
        result.outcome
        is StepExecutionOutcome.ALREADY_EXISTS
    )

    assert (
        result.execution.status
        is ExecutionStatus.ALREADY_EXISTS
    )

    assert result.execution.completed_at is not None

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None

    assert (
        stored.status
        is ExecutionStatus.ALREADY_EXISTS
    )

    assert stored.completed_at is not None