from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from application.dto import StepExecutionOutcome, StepExecutionResult
from application.workflow.checkpoint_service import ExecutionCheckpointService
from application.workflow.step_executor import StepExecutor
from domain.enums import ExecutionStatus
from domain.models import ContractData, ContractExecution


class ContractProcessingError(RuntimeError):
    """Error base de la orquestación completa de un contrato."""


class ContractExecutionIdentityMismatchError(ContractProcessingError):
    """El contrato recibido no corresponde al checkpoint solicitado."""


class ContractProcessingLimitError(ContractProcessingError):
    """La ejecución superó el límite defensivo de transiciones."""


@dataclass(frozen=True, slots=True)
class ContractProcessingResult:
    """Resultado agregado de una ejecución contractual controlada.

    ``StepExecutor`` procesa una sola transición por llamada. Este DTO
    conserva todas las transiciones realizadas por el caso de uso para que
    la API, el runner o las pruebas puedan explicar exactamente dónde se
    detuvo la automatización.
    """

    execution: ContractExecution
    transitions: tuple[StepExecutionResult, ...]

    @property
    def last_result(self) -> StepExecutionResult | None:
        return self.transitions[-1] if self.transitions else None

    @property
    def completed(self) -> bool:
        return self.execution.status is ExecutionStatus.COMPLETED

    @property
    def requires_manual_review(self) -> bool:
        return self.execution.status is ExecutionStatus.MANUAL_REVIEW

    @property
    def retry_pending(self) -> bool:
        return self.execution.status is ExecutionStatus.RETRY_PENDING


class ProcessContract:
    """Ejecuta un contrato hasta alcanzar un punto de detención seguro.

    El caso de uso no conoce Selenium ni SQLite. Coordina únicamente el
    ``StepExecutor`` y el servicio de checkpoints. Cada transición queda
    persistida por esos colaboradores antes de continuar con la siguiente.
    """

    CONTINUABLE_OUTCOMES: frozenset[StepExecutionOutcome] = frozenset(
        {
            StepExecutionOutcome.STEP_CONFIRMED,
            StepExecutionOutcome.STEP_RECONCILED,
        }
    )

    def __init__(
        self,
        *,
        executor: StepExecutor,
        checkpoints: ExecutionCheckpointService,
        max_transitions: int = 32,
    ) -> None:
        if max_transitions <= 0:
            raise ValueError(
                "El límite de transiciones debe ser mayor que cero."
            )

        self._executor = executor
        self._checkpoints = checkpoints
        self._max_transitions = int(max_transitions)

    def execute(self, contract: ContractData) -> ContractProcessingResult:
        """Crea o recupera el checkpoint y procesa el contrato completo."""

        execution = self._checkpoints.create_or_get(
            contract_number=contract.contract_number,
            dependency=contract.dependency,
        )

        return self.execute_existing(
            execution_id=execution.execution_id,
            contract=contract,
        )

    def execute_existing(
        self,
        *,
        execution_id: UUID,
        contract: ContractData,
    ) -> ContractProcessingResult:
        """Continúa una ejecución identificada de forma explícita."""

        execution = self._checkpoints.get(execution_id)
        self._require_same_identity(execution=execution, contract=contract)

        transitions: list[StepExecutionResult] = []

        for _ in range(self._max_transitions):
            result = self._executor.execute_next(
                execution_id=execution_id,
                contract=contract,
            )
            transitions.append(result)

            if result.outcome not in self.CONTINUABLE_OUTCOMES:
                return ContractProcessingResult(
                    execution=result.execution,
                    transitions=tuple(transitions),
                )

        latest = self._checkpoints.get(execution_id)
        raise ContractProcessingLimitError(
            "La ejecución del contrato "
            f"'{latest.contract_number}' superó "
            f"{self._max_transitions} transiciones sin alcanzar un "
            "estado de detención seguro. Revise la máquina de estados."
        )

    @classmethod
    def _require_same_identity(
        cls,
        *,
        execution: ContractExecution,
        contract: ContractData,
    ) -> None:
        same_contract = cls._contract_identity(
            execution.contract_number
        ) == cls._contract_identity(contract.contract_number)
        same_dependency = cls._dependency_identity(
            execution.dependency
        ) == cls._dependency_identity(contract.dependency)

        if same_contract and same_dependency:
            return

        raise ContractExecutionIdentityMismatchError(
            "El checkpoint solicitado no pertenece al contrato recibido. "
            f"Checkpoint: '{execution.contract_number}' / "
            f"'{execution.dependency}'. Contrato: "
            f"'{contract.contract_number}' / '{contract.dependency}'."
        )

    @staticmethod
    def _contract_identity(value: object) -> str:
        return re.sub(r"\s+", "", str(value)).casefold()

    @staticmethod
    def _dependency_identity(value: object) -> str:
        return " ".join(str(value).split()).casefold()
