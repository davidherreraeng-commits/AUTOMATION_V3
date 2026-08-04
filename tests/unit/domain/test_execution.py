<<<<<<< HEAD
import pytest

from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.errors import ExecutionStateError
from domain.models import (
    ContractExecution,
    ExecutionErrorInfo,
)


def test_should_create_pending_execution() -> None:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    assert execution.contract_number == "70-2026"
    assert execution.status is ExecutionStatus.PENDING
    assert execution.last_completed_step is ContractStep.PENDING
    assert execution.current_step is None
    assert execution.attempt_count == 0


def test_should_start_execution_attempt() -> None:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    execution.start_attempt(
        portal_profile="v2026_07",
    )

    assert execution.status is ExecutionStatus.RUNNING
    assert execution.attempt_count == 1
    assert execution.portal_profile == "v2026_07"
    assert execution.started_at is not None


def test_should_preserve_checkpoint_after_retryable_error() -> None:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    execution.start_attempt()
    execution.last_completed_step = ContractStep.CONTRACT_SAVED
    execution.current_step = ContractStep.SUPERVISOR_LINKED

    error = ExecutionErrorInfo(
        code="PORTAL_TIMEOUT",
        category=ErrorCategory.TIMEOUT,
        message="El modal del supervisor no respondió.",
        retryable=True,
    )

    execution.mark_retry_pending(error)

    assert execution.status is ExecutionStatus.RETRY_PENDING
    assert execution.last_completed_step is ContractStep.CONTRACT_SAVED
    assert execution.last_failed_step is ContractStep.SUPERVISOR_LINKED
    assert execution.current_step is None
    assert execution.last_error == error


def test_should_reject_retry_pending_for_non_retryable_error() -> None:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    execution.start_attempt()

    error = ExecutionErrorInfo(
        code="CONTRACTOR_NOT_FOUND",
        category=ErrorCategory.BUSINESS_RULE,
        message="No se encontró el contratista.",
        retryable=False,
    )

    with pytest.raises(
        ExecutionStateError,
        match="no recuperable",
    ):
=======
import pytest

from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.errors import ExecutionStateError
from domain.models import (
    ContractExecution,
    ExecutionErrorInfo,
)


def test_should_create_pending_execution() -> None:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    assert execution.contract_number == "70-2026"
    assert execution.status is ExecutionStatus.PENDING
    assert execution.last_completed_step is ContractStep.PENDING
    assert execution.current_step is None
    assert execution.attempt_count == 0


def test_should_start_execution_attempt() -> None:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    execution.start_attempt(
        portal_profile="v2026_07",
    )

    assert execution.status is ExecutionStatus.RUNNING
    assert execution.attempt_count == 1
    assert execution.portal_profile == "v2026_07"
    assert execution.started_at is not None


def test_should_preserve_checkpoint_after_retryable_error() -> None:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    execution.start_attempt()
    execution.last_completed_step = ContractStep.CONTRACT_SAVED
    execution.current_step = ContractStep.SUPERVISOR_LINKED

    error = ExecutionErrorInfo(
        code="PORTAL_TIMEOUT",
        category=ErrorCategory.TIMEOUT,
        message="El modal del supervisor no respondió.",
        retryable=True,
    )

    execution.mark_retry_pending(error)

    assert execution.status is ExecutionStatus.RETRY_PENDING
    assert execution.last_completed_step is ContractStep.CONTRACT_SAVED
    assert execution.last_failed_step is ContractStep.SUPERVISOR_LINKED
    assert execution.current_step is None
    assert execution.last_error == error


def test_should_reject_retry_pending_for_non_retryable_error() -> None:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )

    execution.start_attempt()

    error = ExecutionErrorInfo(
        code="CONTRACTOR_NOT_FOUND",
        category=ErrorCategory.BUSINESS_RULE,
        message="No se encontró el contratista.",
        retryable=False,
    )

    with pytest.raises(
        ExecutionStateError,
        match="no recuperable",
    ):
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        execution.mark_retry_pending(error)