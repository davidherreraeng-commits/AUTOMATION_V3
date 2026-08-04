from __future__ import annotations

from domain.enums import ContractStep, ExecutionStatus


class DomainError(Exception):
    """Excepción base para errores de las reglas de dominio."""


class ExecutionStateError(DomainError):
    """La ejecución se encuentra en un estado incompatible con la operación."""

    def __init__(
        self,
        message: str,
        *,
        status: ExecutionStatus | None = None,
    ) -> None:
        self.status = status
        super().__init__(message)


class InvalidStepTransitionError(DomainError):
    """Se intentó avanzar a una etapa diferente de la esperada."""

    def __init__(
        self,
        *,
        current_step: ContractStep,
        requested_step: ContractStep,
        expected_step: ContractStep | None,
    ) -> None:
        self.current_step = current_step
        self.requested_step = requested_step
        self.expected_step = expected_step

        expected_value = (
            expected_step.value
            if expected_step is not None
            else "NINGUNA"
        )

        super().__init__(
            "Transición de etapa inválida. "
            f"Etapa completada: {current_step.value}. "
            f"Etapa solicitada: {requested_step.value}. "
            f"Etapa esperada: {expected_value}."
        )


class NoPendingStepError(DomainError):
    """No existen más etapas operativas pendientes."""


class CurrentStepMismatchError(DomainError):
    """La etapa confirmada no corresponde a la etapa actualmente abierta."""

    def __init__(
        self,
        *,
        current_step: ContractStep | None,
        confirmed_step: ContractStep,
    ) -> None:
        self.current_step = current_step
        self.confirmed_step = confirmed_step

        current_value = (
            current_step.value
            if current_step is not None
            else "NINGUNA"
        )

        super().__init__(
            "No se puede confirmar la etapa. "
            f"Etapa actual: {current_value}. "
            f"Etapa recibida: {confirmed_step.value}."
        )