<<<<<<< HEAD
import pytest

from domain.enums import ContractStep, ExecutionStatus
from domain.errors import (
    InvalidStepTransitionError,
    NoPendingStepError,
)
from domain.models import ContractExecution
from domain.services import ContractStateMachine


def create_running_execution() -> ContractExecution:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )
    execution.start_attempt()

    return execution


def test_should_begin_first_step() -> None:
    execution = create_running_execution()

    step = ContractStateMachine.begin_next_step(execution)

    assert step is ContractStep.INPUT_VALIDATED
    assert execution.current_step is ContractStep.INPUT_VALIDATED
    assert execution.last_completed_step is ContractStep.PENDING


def test_should_confirm_current_step() -> None:
    execution = create_running_execution()

    ContractStateMachine.begin_next_step(execution)
    confirmed = ContractStateMachine.confirm_current_step(execution)

    assert confirmed is ContractStep.INPUT_VALIDATED
    assert execution.current_step is None
    assert execution.last_completed_step is ContractStep.INPUT_VALIDATED


def test_should_reject_skipped_step() -> None:
    execution = create_running_execution()

    with pytest.raises(
        InvalidStepTransitionError,
        match="Etapa esperada: INPUT_VALIDATED",
    ):
        ContractStateMachine.begin_step(
            execution,
            ContractStep.HEADER_COMPLETED,
        )


def test_should_resume_from_last_checkpoint() -> None:
    execution = create_running_execution()
    execution.last_completed_step = ContractStep.CONTRACT_SAVED

    next_step = ContractStateMachine.begin_next_step(execution)

    assert next_step is ContractStep.SUPERVISOR_LINKED
    assert execution.current_step is ContractStep.SUPERVISOR_LINKED


def test_should_complete_execution_after_all_steps() -> None:
    execution = create_running_execution()

    for expected_step in ContractStateMachine.STEP_SEQUENCE:
        started_step = ContractStateMachine.begin_next_step(execution)

        assert started_step is expected_step

        ContractStateMachine.confirm_current_step(execution)

    ContractStateMachine.finish(execution)

    assert execution.status is ExecutionStatus.COMPLETED
    assert execution.last_completed_step is ContractStep.COMPLETED
    assert execution.completed_at is not None


def test_should_report_no_pending_steps_before_finish() -> None:
    execution = create_running_execution()

    for _ in ContractStateMachine.STEP_SEQUENCE:
        ContractStateMachine.begin_next_step(execution)
        ContractStateMachine.confirm_current_step(execution)

    with pytest.raises(NoPendingStepError):
=======
import pytest

from domain.enums import ContractStep, ExecutionStatus
from domain.errors import (
    InvalidStepTransitionError,
    NoPendingStepError,
)
from domain.models import ContractExecution
from domain.services import ContractStateMachine


def create_running_execution() -> ContractExecution:
    execution = ContractExecution.create(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
    )
    execution.start_attempt()

    return execution


def test_should_begin_first_step() -> None:
    execution = create_running_execution()

    step = ContractStateMachine.begin_next_step(execution)

    assert step is ContractStep.INPUT_VALIDATED
    assert execution.current_step is ContractStep.INPUT_VALIDATED
    assert execution.last_completed_step is ContractStep.PENDING


def test_should_confirm_current_step() -> None:
    execution = create_running_execution()

    ContractStateMachine.begin_next_step(execution)
    confirmed = ContractStateMachine.confirm_current_step(execution)

    assert confirmed is ContractStep.INPUT_VALIDATED
    assert execution.current_step is None
    assert execution.last_completed_step is ContractStep.INPUT_VALIDATED


def test_should_reject_skipped_step() -> None:
    execution = create_running_execution()

    with pytest.raises(
        InvalidStepTransitionError,
        match="Etapa esperada: INPUT_VALIDATED",
    ):
        ContractStateMachine.begin_step(
            execution,
            ContractStep.HEADER_COMPLETED,
        )


def test_should_resume_from_last_checkpoint() -> None:
    execution = create_running_execution()
    execution.last_completed_step = ContractStep.CONTRACT_SAVED

    next_step = ContractStateMachine.begin_next_step(execution)

    assert next_step is ContractStep.SUPERVISOR_LINKED
    assert execution.current_step is ContractStep.SUPERVISOR_LINKED


def test_should_complete_execution_after_all_steps() -> None:
    execution = create_running_execution()

    for expected_step in ContractStateMachine.STEP_SEQUENCE:
        started_step = ContractStateMachine.begin_next_step(execution)

        assert started_step is expected_step

        ContractStateMachine.confirm_current_step(execution)

    ContractStateMachine.finish(execution)

    assert execution.status is ExecutionStatus.COMPLETED
    assert execution.last_completed_step is ContractStep.COMPLETED
    assert execution.completed_at is not None


def test_should_report_no_pending_steps_before_finish() -> None:
    execution = create_running_execution()

    for _ in ContractStateMachine.STEP_SEQUENCE:
        ContractStateMachine.begin_next_step(execution)
        ContractStateMachine.confirm_current_step(execution)

    with pytest.raises(NoPendingStepError):
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        ContractStateMachine.begin_next_step(execution)