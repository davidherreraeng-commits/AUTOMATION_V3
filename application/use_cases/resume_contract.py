from __future__ import annotations

from uuid import UUID

from application.use_cases.process_contract import (
    ContractProcessingResult,
    ProcessContract,
)
from application.workflow.checkpoint_service import ExecutionCheckpointService
from domain.models import ContractData


class ResumeContract:
    """Reanuda una ejecución existente desde su checkpoint persistido.

    La verificación de identidad se delega a ``ProcessContract``. El
    ``StepExecutor`` decide si debe reconciliar una etapa abierta, comprobar
    un paso fallido antes de repetirlo o continuar con el siguiente paso.
    """

    def __init__(
        self,
        *,
        processor: ProcessContract,
        checkpoints: ExecutionCheckpointService,
    ) -> None:
        self._processor = processor
        self._checkpoints = checkpoints

    def execute(
        self,
        *,
        execution_id: UUID,
        contract: ContractData,
    ) -> ContractProcessingResult:
        # Fuerza un error explícito y estable cuando el identificador no existe
        # antes de delegar la ejecución completa.
        self._checkpoints.get(execution_id)

        return self._processor.execute_existing(
            execution_id=execution_id,
            contract=contract,
        )
