from __future__ import annotations

from uuid import UUID

from application.ports import ContractPortalSessionFactory
from application.use_cases.process_contract import (
    ContractProcessingResult,
    ProcessContract,
)
from application.workflow import ExecutionCheckpointService, StepExecutor
from domain.models import ContractData


class ExecuteContractInSession:
    """Ejecuta o reanuda un contrato dentro de una sola sesión del portal.

    El mismo ``ContractPortal`` se conserva durante todas las transiciones y
    el context manager garantiza el cierre del navegador tanto en éxito como
    ante una excepción.
    """

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
