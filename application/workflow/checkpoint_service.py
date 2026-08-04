from __future__ import annotations

from uuid import UUID

from application.dto import ExecutionResumeState
from application.ports import (
    ExecutionIdentityConflictError,
    ExecutionRepository,
)
from domain.enums import (
    ContractStep,
    ExecutionStatus,
)
from domain.errors import ExecutionStateError
from domain.models import (
    ContractExecution,
    ExecutionErrorInfo,
)
from domain.services.contract_state_machine import ContractStateMachine


class ExecutionCheckpointError(RuntimeError):
    """Error base de la coordinación de checkpoints."""


class ExecutionNotFoundError(ExecutionCheckpointError):
    """No existe una ejecución con el identificador solicitado."""

    def __init__(self, execution_id: UUID) -> None:
        self.execution_id = execution_id

        super().__init__(
            f"No existe la ejecución '{execution_id}'."
        )


class ExecutionCheckpointService:
    """
    Coordina ContractExecution, ContractStateMachine y
    ExecutionRepository.

    Regla central:
        Toda mutación del agregado debe persistirse inmediatamente.

    Esta clase no conoce SQLite directamente. Depende exclusivamente
    del puerto ExecutionRepository.
    """

    NON_RESUMABLE_STATUSES: frozenset[ExecutionStatus] = frozenset(
        {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.ALREADY_EXISTS,
            ExecutionStatus.MANUAL_REVIEW,
            ExecutionStatus.FAILED,
        }
    )

    def __init__(
        self,
        repository: ExecutionRepository,
    ) -> None:
        self._repository = repository

    def create_or_get(
        self,
        *,
        contract_number: str,
        dependency: str,
    ) -> ContractExecution:
        """
        Recupera la ejecución existente o crea una nueva.

        También controla una posible condición de carrera entre:

        1. Consultar que no existe.
        2. Intentar insertar una nueva ejecución.

        Si otro proceso la creó durante ese intervalo, se recupera el
        registro existente en lugar de crear un checkpoint duplicado.
        """

        existing = self._repository.get_by_contract(
            contract_number,
            dependency,
        )

        if existing is not None:
            return existing

        execution = ContractExecution.create(
            contract_number=contract_number,
            dependency=dependency,
        )

        try:
            self._repository.save(execution)
            return execution

        except ExecutionIdentityConflictError:
            concurrent_execution = (
                self._repository.get_by_contract(
                    contract_number,
                    dependency,
                )
            )

            if concurrent_execution is not None:
                return concurrent_execution

            raise

    def get(
        self,
        execution_id: UUID,
    ) -> ContractExecution:
        """Recupera una ejecución o lanza un error explícito."""

        execution = self._repository.get_by_id(
            execution_id
        )

        if execution is None:
            raise ExecutionNotFoundError(
                execution_id
            )

        return execution

    def start_attempt(
        self,
        execution_id: UUID,
        *,
        portal_profile: str | None = None,
    ) -> ContractExecution:
        """
        Inicia un intento y persiste inmediatamente RUNNING.

        Solo es válido desde PENDING o RETRY_PENDING, según las reglas
        del agregado ContractExecution.
        """

        execution = self.get(execution_id)

        execution.start_attempt(
            portal_profile=portal_profile,
        )

        self._repository.save(execution)

        return execution

    def begin_next_step(
        self,
        execution_id: UUID,
    ) -> ContractExecution:
        """
        Abre la siguiente etapa válida y guarda `current_step`.

        Debe invocarse antes de ejecutar la interacción correspondiente
        contra Gestión Transparente.
        """

        execution = self.get(execution_id)

        ContractStateMachine.begin_next_step(
            execution
        )

        self._repository.save(execution)

        return execution

    def confirm_current_step(
        self,
        execution_id: UUID,
        *,
        confirmed_step: ContractStep | None = None,
    ) -> ContractExecution:
        """
        Confirma y persiste la etapa abierta.

        Solo debe llamarse después de comprobar la postcondición en el
        portal. No debe usarse inmediatamente después de un clic sin
        verificación.
        """

        execution = self.get(execution_id)

        ContractStateMachine.confirm_current_step(
            execution,
            confirmed_step,
        )

        self._repository.save(execution)

        return execution

    def mark_retry_pending(
        self,
        execution_id: UUID,
        error: ExecutionErrorInfo,
    ) -> ContractExecution:
        """
        Registra un error recuperable manteniendo el último checkpoint.

        La etapa abierta se traslada a `last_failed_step`.
        """

        execution = self.get(execution_id)

        self._require_running(
            execution,
            operation="marcar un reintento pendiente",
        )

        execution.mark_retry_pending(error)

        self._repository.save(execution)

        return execution

    def mark_failed(
        self,
        execution_id: UUID,
        error: ExecutionErrorInfo,
    ) -> ContractExecution:
        """Registra un error no recuperable automáticamente."""

        execution = self.get(execution_id)

        self._require_running(
            execution,
            operation="marcar la ejecución como fallida",
        )

        execution.mark_failed(error)

        self._repository.save(execution)

        return execution

    def mark_manual_review(
        self,
        execution_id: UUID,
        error: ExecutionErrorInfo,
    ) -> ContractExecution:
        """
        Detiene la automatización y exige revisión humana.
        """

        execution = self.get(execution_id)

        self._require_running(
            execution,
            operation="enviar la ejecución a revisión manual",
        )

        execution.mark_manual_review(error)

        self._repository.save(execution)

        return execution

    def mark_already_exists(
        self,
        execution_id: UUID,
        *,
        message: str,
    ) -> ContractExecution:
        """
        Finaliza la ejecución porque el portal confirmó que el contrato
        ya estaba registrado.
        """

        execution = self.get(execution_id)

        self._require_running(
            execution,
            operation="marcar el contrato como existente",
        )

        execution.mark_already_exists(message)

        self._repository.save(execution)

        return execution

    def finish(
        self,
        execution_id: UUID,
    ) -> ContractExecution:
        """
        Finaliza la ejecución cuando todas las etapas fueron confirmadas.
        """

        execution = self.get(execution_id)

        ContractStateMachine.finish(execution)

        self._repository.save(execution)

        return execution

    def get_resume_state(
        self,
        *,
        contract_number: str,
        dependency: str,
    ) -> ExecutionResumeState | None:
        """
        Determina el punto exacto de recuperación.

        Casos:

        1. No existe ejecución:
           retorna None.

        2. Existe current_step:
           esa etapa estaba abierta y debe reconciliarse.

        3. No existe current_step:
           se calcula la siguiente etapa después del último checkpoint.

        4. Estado terminal o bloqueado:
           no se ofrece una etapa para continuar.
        """

        execution = self._repository.get_by_contract(
            contract_number,
            dependency,
        )

        if execution is None:
            return None

        if execution.status in self.NON_RESUMABLE_STATUSES:
            return ExecutionResumeState(
                execution=execution,
                step=None,
                requires_reconciliation=False,
            )

        if execution.current_step is not None:
            return ExecutionResumeState(
                execution=execution,
                step=execution.current_step,
                requires_reconciliation=True,
            )

        next_step = ContractStateMachine.next_step(
            execution
        )

        return ExecutionResumeState(
            execution=execution,
            step=next_step,
            requires_reconciliation=False,
        )

    @staticmethod
    def _require_running(
        execution: ContractExecution,
        *,
        operation: str,
    ) -> None:
        if execution.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para "
                f"{operation}. Estado actual: "
                f"{execution.status.value}.",
                status=execution.status,
            )