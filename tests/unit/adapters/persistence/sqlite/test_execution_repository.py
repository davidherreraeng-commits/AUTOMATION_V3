from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite import (
    SQLiteExecutionRepository,
)
from application.ports import (
    ExecutionIdentityConflictError,
)
from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.models import (
    ContractExecution,
    ExecutionErrorInfo,
)
from domain.services import ContractStateMachine


def create_repository(
    tmp_path: Path,
) -> SQLiteExecutionRepository:
    return SQLiteExecutionRepository(
        tmp_path / "automation.db"
    )


def create_execution(
    *,
    contract_number: str = "70-2026",
    dependency: str = "Proyectos Especiales",
) -> ContractExecution:
    return ContractExecution.create(
        contract_number=contract_number,
        dependency=dependency,
    )


def advance_until(
    execution: ContractExecution,
    target_step: ContractStep,
) -> None:
    """
    Avanza secuencialmente hasta confirmar `target_step`.
    """

    while (
        execution.last_completed_step
        is not target_step
    ):
        started_step = (
            ContractStateMachine.begin_next_step(
                execution
            )
        )
        ContractStateMachine.confirm_current_step(
            execution,
            started_step,
        )


def test_should_save_and_load_pending_execution(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)
    execution = create_execution()

    repository.save(execution)

    loaded = repository.get_by_id(
        execution.execution_id
    )

    assert loaded is not None
    assert loaded.execution_id == execution.execution_id
    assert loaded.contract_number == "70-2026"
    assert loaded.dependency == "Proyectos Especiales"
    assert loaded.status is ExecutionStatus.PENDING
    assert (
        loaded.last_completed_step
        is ContractStep.PENDING
    )
    assert loaded.attempt_count == 0


def test_should_update_and_restore_checkpoint(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)
    execution = create_execution()

    repository.save(execution)

    execution.start_attempt(
        portal_profile="v2026_07"
    )

    advance_until(
        execution,
        ContractStep.CONTRACT_SAVED,
    )

    repository.save(execution)

    loaded = repository.get_by_id(
        execution.execution_id
    )

    assert loaded is not None
    assert loaded.status is ExecutionStatus.RUNNING
    assert loaded.attempt_count == 1
    assert loaded.portal_profile == "v2026_07"
    assert (
        loaded.last_completed_step
        is ContractStep.CONTRACT_SAVED
    )
    assert loaded.current_step is None
    assert loaded.started_at is not None


def test_should_restore_retryable_error(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)
    execution = create_execution()

    execution.start_attempt(
        portal_profile="v2026_07"
    )

    advance_until(
        execution,
        ContractStep.CONTRACT_SAVED,
    )

    ContractStateMachine.begin_next_step(
        execution
    )

    error = ExecutionErrorInfo(
        code="PORTAL_TIMEOUT",
        category=ErrorCategory.TIMEOUT,
        message=(
            "El modal del supervisor no respondió."
        ),
        retryable=True,
        metadata={
            "locator": "supervisor.dialog",
            "attempt": 1,
        },
    )

    execution.mark_retry_pending(error)

    repository.save(execution)

    loaded = repository.get_by_contract(
        "70-2026",
        "Proyectos Especiales",
    )

    assert loaded is not None
    assert (
        loaded.status
        is ExecutionStatus.RETRY_PENDING
    )
    assert (
        loaded.last_completed_step
        is ContractStep.CONTRACT_SAVED
    )
    assert (
        loaded.last_failed_step
        is ContractStep.SUPERVISOR_LINKED
    )
    assert loaded.current_step is None
    assert loaded.last_error is not None
    assert loaded.last_error.code == "PORTAL_TIMEOUT"
    assert loaded.last_error.retryable
    assert loaded.last_error.metadata == {
        "attempt": 1,
        "locator": "supervisor.dialog",
    }


def test_should_find_contract_using_normalized_identity(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    execution = create_execution(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )
    repository.save(execution)

    loaded = repository.get_by_contract(
        " 70 - 2026 ",
        "proyectos   especiales",
    )

    assert loaded is not None
    assert loaded.execution_id == execution.execution_id


def test_should_filter_executions_by_status(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    pending = create_execution(
        contract_number="70-2026"
    )

    retry_pending = create_execution(
        contract_number="71-2026"
    )
    retry_pending.start_attempt()

    error = ExecutionErrorInfo(
        code="PORTAL_TIMEOUT",
        category=ErrorCategory.TIMEOUT,
        message="Timeout recuperable.",
        retryable=True,
    )
    retry_pending.mark_retry_pending(error)

    completed = create_execution(
        contract_number="72-2026"
    )
    completed.start_attempt()

    for _ in ContractStateMachine.STEP_SEQUENCE:
        ContractStateMachine.begin_next_step(
            completed
        )
        ContractStateMachine.confirm_current_step(
            completed
        )

    ContractStateMachine.finish(completed)

    repository.save(pending)
    repository.save(retry_pending)
    repository.save(completed)

    results = repository.list_by_status(
        {
            ExecutionStatus.PENDING,
            ExecutionStatus.RETRY_PENDING,
        }
    )

    assert {
        execution.contract_number
        for execution in results
    } == {
        "70-2026",
        "71-2026",
    }


def test_should_reject_different_execution_for_same_identity(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    first = create_execution(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    second = ContractExecution(
        execution_id=uuid4(),
        contract_number=" 70-2026 ",
        dependency="proyectos especiales",
    )

    repository.save(first)

    with pytest.raises(
        ExecutionIdentityConflictError,
        match="Ya existe otra ejecución",
    ):
        repository.save(second)


def test_should_return_none_for_unknown_execution(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    assert repository.get_by_id(uuid4()) is None

    assert repository.get_by_contract(
        "999-2026",
        "Proyectos Especiales",
    ) is None