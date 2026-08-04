from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from application.dto import StepExecutionOutcome, StepExecutionResult
from application.use_cases.process_contract import ContractProcessingResult
from domain.enums import ContractStep, ExecutionStatus
from domain.models import ContractData, ContractExecution


class DryRunContractExecutor:
    """Simula todas las transiciones sin abrir navegador ni persistir checkpoints reales."""

    STEPS: tuple[ContractStep, ...] = (
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

    def execute(
        self,
        *,
        contract: ContractData,
        execution_id: UUID | None = None,
    ) -> ContractProcessingResult:
        started_at = datetime.now(UTC)
        correlation_execution_id = execution_id or uuid4()
        completed_at = datetime.now(UTC)

        execution = ContractExecution(
            execution_id=correlation_execution_id,
            contract_number=contract.contract_number,
            dependency=contract.dependency,
            status=ExecutionStatus.COMPLETED,
            last_completed_step=ContractStep.COMPLETED,
            current_step=None,
            last_failed_step=None,
            attempt_count=1,
            portal_profile="DRY_RUN",
            last_error=None,
            created_at=started_at,
            started_at=started_at,
            updated_at=completed_at,
            completed_at=completed_at,
        )

        transitions = tuple(
            StepExecutionResult(
                execution=execution,
                outcome=StepExecutionOutcome.STEP_CONFIRMED,
                step=step,
                message=(
                    f"Simulación confirmada para la etapa {step.value}; "
                    "no se realizó ninguna interacción con el portal."
                ),
            )
            for step in self.STEPS
        ) + (
            StepExecutionResult(
                execution=execution,
                outcome=StepExecutionOutcome.COMPLETED,
                step=ContractStep.COMPLETED,
                message=(
                    "Simulación completa. No se abrió Chrome ni se escribieron "
                    "datos en Gestión Transparente."
                ),
            ),
        )

        return ContractProcessingResult(
            execution=execution,
            transitions=transitions,
        )
