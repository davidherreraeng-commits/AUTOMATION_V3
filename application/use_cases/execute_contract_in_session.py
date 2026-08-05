from __future__ import annotations

from uuid import UUID

from application.dto import PortalVerificationStatus
from application.ports import ContractPortal, ContractPortalSessionFactory
from application.use_cases.process_contract import (
    ContractProcessingResult,
    ProcessContract,
)
from application.workflow import ExecutionCheckpointService, StepExecutor
from domain.enums import ContractStep, ExecutionStatus
from domain.errors import PortalValidationError
from domain.models import ContractData, ContractExecution


class ExecuteContractInSession:
    """Ejecuta o reanuda un contrato dentro de una sola sesión del portal.

    El mismo ``ContractPortal`` se conserva durante todas las transiciones y
    el context manager garantiza el cierre del navegador tanto en éxito como
    ante una excepción.

    Los checkpoints anteriores a ``CONTRACT_SAVED`` representan estado
    transitorio del formulario. Cuando una reanudación abre un navegador
    nuevo, ese estado no existe en Gestión Transparente y debe reconstruirse
    de forma segura antes de continuar con el paso fallido.
    """

    PRE_PERSISTENCE_PORTAL_STEPS: tuple[ContractStep, ...] = (
        ContractStep.ASSISTANT_OPENED,
        ContractStep.HEADER_COMPLETED,
        ContractStep.HEADER_VALIDATED,
        ContractStep.GENERAL_DATA_COMPLETED,
    )

    def __init__(
        self,
        *,
        sessions: ContractPortalSessionFactory,
        checkpoints: ExecutionCheckpointService,
        max_transitions: int = 32,
    ) -> None:
        if max_transitions <= 0:
            raise ValueError(
                "El límite de transiciones debe ser mayor que cero."
            )
        self._sessions = sessions
        self._checkpoints = checkpoints
        self._max_transitions = int(max_transitions)

    def execute(
        self,
        *,
        contract: ContractData,
        execution_id: UUID | None = None,
    ) -> ContractProcessingResult:
        """Procesa un contrato nuevo o recupera un checkpoint existente."""

        with self._sessions.open(
            dependency=contract.dependency,
        ) as opened:
            if execution_id is not None:
                execution = self._checkpoints.get(execution_id)
                self._replay_pre_persistence_state(
                    portal=opened.portal,
                    execution=execution,
                    contract=contract,
                )

            executor = StepExecutor(
                portal=opened.portal,
                checkpoints=self._checkpoints,
                portal_profile=opened.profile,
            )
            processor = ProcessContract(
                executor=executor,
                checkpoints=self._checkpoints,
                max_transitions=self._max_transitions,
            )
            if execution_id is None:
                return processor.execute(contract)
            return processor.execute_existing(
                execution_id=execution_id,
                contract=contract,
            )

    def _replay_pre_persistence_state(
        self,
        *,
        portal: ContractPortal,
        execution: ContractExecution,
        contract: ContractData,
    ) -> None:
        """Reconstruye solo el formulario transitorio en una sesión nueva.

        Esta operación no modifica checkpoints. Repite únicamente acciones
        anteriores al primer guardado institucional y verifica cada
        postcondición antes de avanzar. Nunca repite ``CONTRACT_SAVED`` ni
        pasos posteriores.
        """

        replay_steps = self._steps_to_replay(execution)
        for step in replay_steps:
            portal.execute_step(step, contract)
            verification = portal.verify_step(step, contract)
            if verification.status is PortalVerificationStatus.CONFIRMED:
                continue

            raise PortalValidationError(
                (
                    "No fue posible reconstruir el estado transitorio "
                    f"del portal en la etapa {step.value}."
                ),
                code="PRE_PERSISTENCE_REPLAY_FAILED",
                retryable=True,
                metadata={
                    "step": step.value,
                    "verification_status": verification.status.value,
                    **dict(verification.metadata),
                },
            )

    @classmethod
    def _steps_to_replay(
        cls,
        execution: ContractExecution,
    ) -> tuple[ContractStep, ...]:
        """Calcula el prefijo transitorio que debe reejecutarse."""

        if execution.status is not ExecutionStatus.RETRY_PENDING:
            return ()

        last_completed = execution.last_completed_step
        if last_completed not in cls.PRE_PERSISTENCE_PORTAL_STEPS:
            return ()

        last_index = cls.PRE_PERSISTENCE_PORTAL_STEPS.index(
            last_completed
        )
        return cls.PRE_PERSISTENCE_PORTAL_STEPS[: last_index + 1]
