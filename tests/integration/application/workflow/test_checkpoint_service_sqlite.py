from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite import SQLiteExecutionRepository
from application.workflow import (
    ExecutionCheckpointService,
    ExecutionNotFoundError,
)
from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.models import ExecutionErrorInfo
from domain.services.contract_state_machine import ContractStateMachine


def create_service(
    tmp_path: Path,
) -> tuple[
    ExecutionCheckpointService,
    SQLiteExecutionRepository,
]:
    """
    Construye el servicio de checkpoints con una base SQLite temporal.

    pytest proporciona un directorio aislado mediante tmp_path para
    que cada prueba utilice su propia base de datos.
    """

    repository = SQLiteExecutionRepository(
        tmp_path / "checkpoints.db"
    )

    service = ExecutionCheckpointService(
        repository
    )

    return service, repository


def create_execution(
    service: ExecutionCheckpointService,
):
    """
    Crea o recupera la ejecución utilizada en la mayoría de pruebas.
    """

    return service.create_or_get(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )


def test_should_create_or_recover_same_execution(
    tmp_path: Path,
) -> None:
    service, repository = create_service(
        tmp_path
    )

    first = create_execution(service)

    second = service.create_or_get(
        contract_number=" 70-2026 ",
        dependency="proyectos   especiales",
    )

    assert first.execution_id == second.execution_id

    stored = repository.get_by_id(
        first.execution_id
    )

    assert stored is not None
    assert stored.status is ExecutionStatus.PENDING
    assert stored.attempt_count == 0
    assert stored.current_step is None
    assert (
        stored.last_completed_step
        is ContractStep.PENDING
    )


def test_should_persist_started_attempt(
    tmp_path: Path,
) -> None:
    service, repository = create_service(
        tmp_path
    )

    execution = create_execution(service)

    started = service.start_attempt(
        execution.execution_id,
        portal_profile="v2026_07",
    )

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert started.status is ExecutionStatus.RUNNING
    assert started.attempt_count == 1
    assert started.portal_profile == "v2026_07"
    assert started.started_at is not None

    assert stored is not None
    assert stored.status is ExecutionStatus.RUNNING
    assert stored.attempt_count == 1
    assert stored.portal_profile == "v2026_07"
    assert stored.started_at is not None


def test_should_persist_open_and_confirmed_step(
    tmp_path: Path,
) -> None:
    service, repository = create_service(
        tmp_path
    )

    execution = create_execution(service)

    service.start_attempt(
        execution.execution_id
    )

    opened = service.begin_next_step(
        execution.execution_id
    )

    assert (
        opened.current_step
        is ContractStep.INPUT_VALIDATED
    )
    assert (
        opened.last_completed_step
        is ContractStep.PENDING
    )

    stored_opened = repository.get_by_id(
        execution.execution_id
    )

    assert stored_opened is not None
    assert (
        stored_opened.current_step
        is ContractStep.INPUT_VALIDATED
    )
    assert (
        stored_opened.last_completed_step
        is ContractStep.PENDING
    )

    confirmed = service.confirm_current_step(
        execution.execution_id,
        confirmed_step=ContractStep.INPUT_VALIDATED,
    )

    assert confirmed.current_step is None
    assert (
        confirmed.last_completed_step
        is ContractStep.INPUT_VALIDATED
    )

    stored_confirmed = repository.get_by_id(
        execution.execution_id
    )

    assert stored_confirmed is not None
    assert stored_confirmed.current_step is None
    assert (
        stored_confirmed.last_completed_step
        is ContractStep.INPUT_VALIDATED
    )


def test_should_require_reconciliation_for_open_step(
    tmp_path: Path,
) -> None:
    service, _ = create_service(tmp_path)

    execution = create_execution(service)

    service.start_attempt(
        execution.execution_id
    )

    service.begin_next_step(
        execution.execution_id
    )

    resume_state = service.get_resume_state(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    assert resume_state is not None
    assert resume_state.can_continue
    assert resume_state.requires_reconciliation

    assert (
        resume_state.step
        is ContractStep.INPUT_VALIDATED
    )

    assert (
        resume_state.execution.current_step
        is ContractStep.INPUT_VALIDATED
    )


def test_should_return_next_step_after_confirmed_checkpoint(
    tmp_path: Path,
) -> None:
    service, _ = create_service(tmp_path)

    execution = create_execution(service)

    service.start_attempt(
        execution.execution_id
    )

    service.begin_next_step(
        execution.execution_id
    )

    service.confirm_current_step(
        execution.execution_id
    )

    resume_state = service.get_resume_state(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    assert resume_state is not None
    assert resume_state.can_continue
    assert not resume_state.requires_reconciliation

    assert (
        resume_state.step
        is ContractStep.ASSISTANT_OPENED
    )

    assert (
        resume_state.execution.last_completed_step
        is ContractStep.INPUT_VALIDATED
    )


def test_should_persist_retry_and_start_second_attempt(
    tmp_path: Path,
) -> None:
    service, repository = create_service(
        tmp_path
    )

    execution = create_execution(service)

    service.start_attempt(
        execution.execution_id
    )

    service.begin_next_step(
        execution.execution_id
    )

    error = ExecutionErrorInfo(
        code="PORTAL_TIMEOUT",
        category=ErrorCategory.TIMEOUT,
        message="El portal no respondió.",
        retryable=True,
        metadata={
            "locator": "contract.header",
        },
    )

    retry_pending = service.mark_retry_pending(
        execution.execution_id,
        error,
    )

    assert (
        retry_pending.status
        is ExecutionStatus.RETRY_PENDING
    )

    assert (
        retry_pending.last_failed_step
        is ContractStep.INPUT_VALIDATED
    )

    assert (
        retry_pending.last_completed_step
        is ContractStep.PENDING
    )

    assert retry_pending.current_step is None
    assert retry_pending.last_error == error

    restarted = service.start_attempt(
        execution.execution_id,
        portal_profile="v2026_07",
    )

    assert restarted.status is ExecutionStatus.RUNNING
    assert restarted.attempt_count == 2
    assert restarted.last_error is None
    assert restarted.current_step is None

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None
    assert stored.attempt_count == 2
    assert stored.status is ExecutionStatus.RUNNING
    assert stored.last_error is None


def test_should_persist_non_retryable_failure(
    tmp_path: Path,
) -> None:
    service, repository = create_service(
        tmp_path
    )

    execution = create_execution(service)

    service.start_attempt(
        execution.execution_id
    )

    service.begin_next_step(
        execution.execution_id
    )

    error = ExecutionErrorInfo(
        code="CONTRACTOR_NOT_FOUND",
        category=ErrorCategory.BUSINESS_RULE,
        message="No se encontró el contratista.",
        retryable=False,
        metadata={
            "document": "900469775-8",
        },
    )

    failed = service.mark_failed(
        execution.execution_id,
        error,
    )

    assert failed.status is ExecutionStatus.FAILED
    assert failed.current_step is None

    assert (
        failed.last_failed_step
        is ContractStep.INPUT_VALIDATED
    )

    assert failed.last_error is not None
    assert failed.last_error.code == "CONTRACTOR_NOT_FOUND"

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None
    assert stored.status is ExecutionStatus.FAILED
    assert stored.last_error is not None
    assert stored.last_error.metadata == {
        "document": "900469775-8",
    }


def test_should_persist_manual_review_status(
    tmp_path: Path,
) -> None:
    service, repository = create_service(
        tmp_path
    )

    execution = create_execution(service)

    service.start_attempt(
        execution.execution_id
    )

    service.begin_next_step(
        execution.execution_id
    )

    error = ExecutionErrorInfo(
        code="AMBIGUOUS_PORTAL_STATE",
        category=ErrorCategory.PORTAL_STRUCTURE,
        message=(
            "No fue posible determinar si la etapa ya fue aplicada."
        ),
        retryable=False,
    )

    manual_review = service.mark_manual_review(
        execution.execution_id,
        error,
    )

    assert (
        manual_review.status
        is ExecutionStatus.MANUAL_REVIEW
    )

    assert manual_review.current_step is None

    assert (
        manual_review.last_failed_step
        is ContractStep.INPUT_VALIDATED
    )

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None

    assert (
        stored.status
        is ExecutionStatus.MANUAL_REVIEW
    )


def test_should_finish_and_persist_completed_execution(
    tmp_path: Path,
) -> None:
    service, repository = create_service(
        tmp_path
    )

    execution = create_execution(service)

    service.start_attempt(
        execution.execution_id
    )

    for expected_step in (
        ContractStateMachine.STEP_SEQUENCE
    ):
        opened = service.begin_next_step(
            execution.execution_id
        )

        assert opened.current_step is expected_step

        confirmed = service.confirm_current_step(
            execution.execution_id,
            confirmed_step=expected_step,
        )

        assert confirmed.current_step is None
        assert (
            confirmed.last_completed_step
            is expected_step
        )

    completed = service.finish(
        execution.execution_id
    )

    assert completed.status is ExecutionStatus.COMPLETED

    assert (
        completed.last_completed_step
        is ContractStep.COMPLETED
    )

    assert completed.completed_at is not None
    assert completed.current_step is None

    stored = repository.get_by_id(
        execution.execution_id
    )

    assert stored is not None
    assert stored.status is ExecutionStatus.COMPLETED

    assert (
        stored.last_completed_step
        is ContractStep.COMPLETED
    )

    assert stored.completed_at is not None


def test_should_not_offer_resume_step_for_terminal_execution(
    tmp_path: Path,
) -> None:
    service, _ = create_service(tmp_path)

    execution = create_execution(service)

    service.start_attempt(
        execution.execution_id
    )

    service.mark_already_exists(
        execution.execution_id,
        message=(
            "El contrato ya se encuentra registrado."
        ),
    )

    resume_state = service.get_resume_state(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    assert resume_state is not None
    assert resume_state.is_finished
    assert not resume_state.can_continue
    assert resume_state.step is None
    assert not resume_state.requires_reconciliation

    assert (
        resume_state.execution.status
        is ExecutionStatus.ALREADY_EXISTS
    )


def test_should_return_none_for_contract_without_execution(
    tmp_path: Path,
) -> None:
    service, _ = create_service(tmp_path)

    resume_state = service.get_resume_state(
        contract_number="999-2026",
        dependency="Proyectos Especiales",
    )

    assert resume_state is None


def test_should_raise_for_unknown_execution(
    tmp_path: Path,
) -> None:
    service, _ = create_service(tmp_path)

    unknown_id = uuid4()

    with pytest.raises(
        ExecutionNotFoundError,
        match=str(unknown_id),
    ):
        service.start_attempt(
            unknown_id
        )