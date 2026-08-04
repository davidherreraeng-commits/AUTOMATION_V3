from __future__ import annotations

from domain.enums import ContractStep, ExecutionStatus
from domain.errors import (
    CurrentStepMismatchError,
    ExecutionStateError,
    InvalidStepTransitionError,
    NoPendingStepError,
)
from domain.models.execution import ContractExecution


class ContractStateMachine:
    """
    Controla el orden permitido de las etapas del registro contractual.

    Una etapa solo se considera completada después de que el adaptador
    del portal compruebe su postcondición y solicite su confirmación.

    La máquina de estados no conoce Selenium, SQLite, Excel ni el portal.
    """

    STEP_SEQUENCE: tuple[ContractStep, ...] = (
        ContractStep.INPUT_VALIDATED,
        ContractStep.ASSISTANT_OPENED,
        ContractStep.HEADER_COMPLETED,
        ContractStep.HEADER_VALIDATED,
        ContractStep.GENERAL_DATA_COMPLETED,
        ContractStep.CONTRACT_SAVED,
        ContractStep.SUPERVISOR_LINKED,
        ContractStep.AVAILABILITY_LINKED,
        ContractStep.BUDGET_REGISTER_LINKED,
        ContractStep.ADDITIONAL_DATES_LINKED,
    )

    @classmethod
    def next_step(
        cls,
        execution: ContractExecution,
    ) -> ContractStep | None:
        """
        Determina la siguiente etapa según el último checkpoint confirmado.

        Devuelve None cuando no quedan etapas operativas pendientes.
        """

        if execution.last_completed_step == ContractStep.COMPLETED:
            return None

        if execution.last_completed_step == ContractStep.PENDING:
            return cls.STEP_SEQUENCE[0]

        try:
            current_index = cls.STEP_SEQUENCE.index(
                execution.last_completed_step
            )
        except ValueError as error:
            raise ExecutionStateError(
                "La última etapa completada no pertenece a la "
                "secuencia conocida: "
                f"{execution.last_completed_step.value}."
            ) from error

        next_index = current_index + 1

        if next_index >= len(cls.STEP_SEQUENCE):
            return None

        return cls.STEP_SEQUENCE[next_index]

    @classmethod
    def begin_next_step(
        cls,
        execution: ContractExecution,
    ) -> ContractStep:
        """
        Abre la siguiente etapa válida y devuelve su identificador.
        """

        expected_step = cls.next_step(execution)

        if expected_step is None:
            raise NoPendingStepError(
                "La ejecución no tiene etapas operativas pendientes."
            )

        cls.begin_step(
            execution,
            expected_step,
        )

        return expected_step

    @classmethod
    def begin_step(
        cls,
        execution: ContractExecution,
        requested_step: ContractStep,
    ) -> None:
        """
        Abre una etapa concreta.

        La etapa solicitada debe coincidir exactamente con la siguiente
        transición permitida.
        """

        if execution.status != ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para iniciar "
                "una etapa.",
                status=execution.status,
            )

        expected_step = cls.next_step(execution)

        if requested_step != expected_step:
            raise InvalidStepTransitionError(
                current_step=execution.last_completed_step,
                requested_step=requested_step,
                expected_step=expected_step,
            )

        execution._begin_step(requested_step)

    @classmethod
    def confirm_current_step(
        cls,
        execution: ContractExecution,
        confirmed_step: ContractStep | None = None,
    ) -> ContractStep:
        """
        Confirma la etapa actualmente abierta.

        Debe utilizarse solamente después de verificar la postcondición
        correspondiente en Gestión Transparente.
        """

        current_step = execution.current_step
        step_to_confirm = confirmed_step or current_step

        if step_to_confirm is None:
            raise ExecutionStateError(
                "No existe una etapa abierta para confirmar."
            )

        if current_step != step_to_confirm:
            raise CurrentStepMismatchError(
                current_step=current_step,
                confirmed_step=step_to_confirm,
            )

        execution._confirm_step(step_to_confirm)

        return step_to_confirm

    @classmethod
    def finish(
        cls,
        execution: ContractExecution,
    ) -> None:
        """
        Marca la ejecución completa.

        Solo puede finalizarse después de confirmar la última etapa
        operativa: ADDITIONAL_DATES_LINKED.
        """

        if execution.status != ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para finalizar.",
                status=execution.status,
            )

        if execution.current_step is not None:
            raise ExecutionStateError(
                "No se puede finalizar mientras exista una etapa "
                f"abierta: {execution.current_step.value}."
            )

        expected_last_step = cls.STEP_SEQUENCE[-1]

        if execution.last_completed_step != expected_last_step:
            raise InvalidStepTransitionError(
                current_step=execution.last_completed_step,
                requested_step=ContractStep.COMPLETED,
                expected_step=cls.next_step(execution),
            )

        execution._mark_completed()