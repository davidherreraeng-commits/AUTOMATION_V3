from __future__ import annotations

from dataclasses import dataclass

from domain.enums import (
    ContractStep,
    ExecutionStatus,
)
from domain.models import ContractExecution


@dataclass(frozen=True, slots=True)
class ExecutionResumeState:
    """
    Estado necesario para decidir cómo continuar una ejecución.

    step:
        Etapa que debe ejecutarse o reconciliarse.

    requires_reconciliation:
        True cuando SQLite indica que una etapa había comenzado, pero
        no existe confirmación persistida de su postcondición.

        En ese caso no debe repetirse automáticamente la acción web.
        Primero debe consultarse el estado actual del portal.
    """

    execution: ContractExecution
    step: ContractStep | None
    requires_reconciliation: bool

    @property
    def can_continue(self) -> bool:
        """
        Indica si la ejecución puede continuar automáticamente.

        FAILED y MANUAL_REVIEW requieren una decisión explícita.
        COMPLETED y ALREADY_EXISTS ya no tienen trabajo pendiente.
        """

        return (
            self.step is not None
            and self.execution.status
            in {
                ExecutionStatus.PENDING,
                ExecutionStatus.RUNNING,
                ExecutionStatus.RETRY_PENDING,
            }
        )

    @property
    def is_finished(self) -> bool:
        return self.execution.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.ALREADY_EXISTS,
        }