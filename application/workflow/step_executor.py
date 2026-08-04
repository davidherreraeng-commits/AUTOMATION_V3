<<<<<<< HEAD
from __future__ import annotations

from uuid import UUID

from application.dto import (
    PortalStepVerification,
    PortalVerificationStatus,
    StepExecutionOutcome,
    StepExecutionResult,
)
from application.ports import ContractPortal
from application.workflow.checkpoint_service import (
    ExecutionCheckpointService,
)
from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.errors import (
    PortalAlreadyExistsError,
    PortalAutomationError,
    PortalStructureChangedError,
)
from domain.models import (
    ContractData,
    ContractExecution,
    ExecutionErrorInfo,
)


class StepExecutor:
    """
    Ejecuta una etapa contractual de forma persistente e idempotente.

    Responsabilidades:

    1. Recuperar el checkpoint de la ejecución.
    2. Iniciar un intento cuando corresponda.
    3. Abrir la siguiente etapa.
    4. Ejecutar la acción en el portal.
    5. Verificar la postcondición.
    6. Confirmar el checkpoint.
    7. Clasificar y persistir errores.
    8. Reconciliar etapas interrumpidas.
    """

    TERMINAL_STATUSES: frozenset[ExecutionStatus] = frozenset(
        {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.ALREADY_EXISTS,
            ExecutionStatus.MANUAL_REVIEW,
            ExecutionStatus.FAILED,
        }
    )

    STARTABLE_STATUSES: frozenset[ExecutionStatus] = frozenset(
        {
            ExecutionStatus.PENDING,
            ExecutionStatus.RETRY_PENDING,
        }
    )

    def __init__(
        self,
        *,
        portal: ContractPortal,
        checkpoints: ExecutionCheckpointService,
        portal_profile: str | None = None,
    ) -> None:
        self._portal = portal
        self._checkpoints = checkpoints
        self._portal_profile = portal_profile

    def execute_next(
        self,
        *,
        execution_id: UUID,
        contract: ContractData,
    ) -> StepExecutionResult:
        """
        Ejecuta o reconcilia una única etapa.

        Una llamada a este método procesa como máximo una etapa.
        """

        execution = self._checkpoints.get(
            execution_id
        )

        if execution.status in self.TERMINAL_STATUSES:
            return StepExecutionResult(
                execution=execution,
                outcome=StepExecutionOutcome.NO_ACTION,
                step=None,
                message=(
                    "La ejecución no admite acciones automáticas "
                    f"desde el estado {execution.status.value}."
                ),
            )

        if execution.status in self.STARTABLE_STATUSES:
            execution = self._checkpoints.start_attempt(
                execution.execution_id,
                portal_profile=self._portal_profile,
            )

        resume_state = self._checkpoints.get_resume_state(
            contract_number=contract.contract_number,
            dependency=contract.dependency,
        )

        if resume_state is None:
            raise RuntimeError(
                "No fue posible recuperar el checkpoint del contrato "
                "después de iniciar el intento."
            )

        if resume_state.step is None:
            return self._finish_if_ready(
                resume_state.execution
            )

        if resume_state.requires_reconciliation:
            return self._reconcile_open_step(
                execution=resume_state.execution,
                step=resume_state.step,
                contract=contract,
            )

        opened_execution = (
            self._checkpoints.begin_next_step(
                execution.execution_id
            )
        )

        step = opened_execution.current_step

        if step is None:
            raise RuntimeError(
                "El servicio de checkpoints no dejó una etapa abierta."
            )

        # ContractData ya fue construido y validado antes de llegar
        # al portal. INPUT_VALIDATED no necesita Selenium.
        if step is ContractStep.INPUT_VALIDATED:
            confirmed_execution = (
                self._checkpoints.confirm_current_step(
                    execution.execution_id,
                    confirmed_step=step,
                )
            )

            return StepExecutionResult(
                execution=confirmed_execution,
                outcome=(
                    StepExecutionOutcome.STEP_CONFIRMED
                ),
                step=step,
                message=(
                    "Los datos de entrada fueron validados."
                ),
            )

        return self._execute_open_step(
            execution=opened_execution,
            step=step,
            contract=contract,
        )

    def _reconcile_open_step(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        contract: ContractData,
    ) -> StepExecutionResult:
        """
        Determina qué ocurrió con una etapa que quedó abierta.

        La etapa pudo haber sido aplicada en el portal antes de que el
        proceso se interrumpiera. Por ello primero se verifica y no se
        repite automáticamente.
        """

        try:
            verification = self._portal.verify_step(
                step,
                contract,
            )

        except PortalAlreadyExistsError as error:
            return self._mark_already_exists(
                execution=execution,
                step=step,
                error=error,
            )

        except PortalAutomationError as error:
            return self._handle_portal_error(
                execution=execution,
                step=step,
                error=error,
            )

        except Exception as error:
            return self._handle_unknown_error(
                execution=execution,
                step=step,
                error=error,
            )

        if (
            verification.status
            is PortalVerificationStatus.CONFIRMED
        ):
            confirmed_execution = (
                self._checkpoints.confirm_current_step(
                    execution.execution_id,
                    confirmed_step=step,
                )
            )

            return StepExecutionResult(
                execution=confirmed_execution,
                outcome=(
                    StepExecutionOutcome.STEP_RECONCILED
                ),
                step=step,
                message=(
                    verification.message
                    or (
                        "La etapa interrumpida ya estaba "
                        "aplicada en el portal."
                    )
                ),
            )

        if (
            verification.status
            is PortalVerificationStatus.NOT_APPLIED
        ):
            return self._execute_open_step(
                execution=execution,
                step=step,
                contract=contract,
            )

        return self._mark_ambiguous(
            execution=execution,
            step=step,
            verification=verification,
        )

    def _execute_open_step(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        contract: ContractData,
    ) -> StepExecutionResult:
        """
        Ejecuta una etapa abierta y verifica su postcondición.
        """

        try:
            self._portal.execute_step(
                step,
                contract,
            )

            verification = self._portal.verify_step(
                step,
                contract,
            )

            if (
                verification.status
                is PortalVerificationStatus.CONFIRMED
            ):
                confirmed_execution = (
                    self._checkpoints.confirm_current_step(
                        execution.execution_id,
                        confirmed_step=step,
                    )
                )

                return StepExecutionResult(
                    execution=confirmed_execution,
                    outcome=(
                        StepExecutionOutcome.STEP_CONFIRMED
                    ),
                    step=step,
                    message=(
                        verification.message
                        or "La etapa fue confirmada."
                    ),
                )

            if (
                verification.status
                is PortalVerificationStatus.AMBIGUOUS
            ):
                return self._mark_ambiguous(
                    execution=execution,
                    step=step,
                    verification=verification,
                )

            error_info = ExecutionErrorInfo(
                code="STEP_POSTCONDITION_NOT_CONFIRMED",
                category=ErrorCategory.PORTAL_VALIDATION,
                message=(
                    verification.message
                    or (
                        "La acción fue ejecutada, pero el portal "
                        "no confirmó su postcondición."
                    )
                ),
                retryable=True,
                metadata={
                    "step": step.value,
                    **dict(verification.metadata),
                },
            )

            retry_pending = (
                self._checkpoints.mark_retry_pending(
                    execution.execution_id,
                    error_info,
                )
            )

            self._safe_recover()

            return StepExecutionResult(
                execution=retry_pending,
                outcome=StepExecutionOutcome.RETRY_PENDING,
                step=step,
                message=error_info.message,
            )

        except PortalAlreadyExistsError as error:
            return self._mark_already_exists(
                execution=execution,
                step=step,
                error=error,
            )

        except PortalAutomationError as error:
            return self._handle_portal_error(
                execution=execution,
                step=step,
                error=error,
            )

        except Exception as error:
            return self._handle_unknown_error(
                execution=execution,
                step=step,
                error=error,
            )

    def _mark_already_exists(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        error: PortalAlreadyExistsError,
    ) -> StepExecutionResult:
        """
        Finaliza la ejecución porque el portal confirmó que el contrato
        ya estaba registrado.
        """

        already_exists = (
            self._checkpoints.mark_already_exists(
                execution.execution_id,
                message=str(error),
            )
        )

        return StepExecutionResult(
            execution=already_exists,
            outcome=(
                StepExecutionOutcome.ALREADY_EXISTS
            ),
            step=step,
            message=str(error),
        )

    def _handle_portal_error(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        error: PortalAutomationError,
    ) -> StepExecutionResult:
        """
        Convierte una excepción conocida del portal en un error
        persistible.
        """

        error_info = ExecutionErrorInfo(
            code=error.code,
            category=error.category,
            message=str(error),
            retryable=error.retryable,
            metadata={
                "step": step.value,
                **error.metadata,
            },
        )

        self._safe_recover()

        if error.retryable:
            retry_pending = (
                self._checkpoints.mark_retry_pending(
                    execution.execution_id,
                    error_info,
                )
            )

            return StepExecutionResult(
                execution=retry_pending,
                outcome=StepExecutionOutcome.RETRY_PENDING,
                step=step,
                message=str(error),
            )

        if isinstance(
            error,
            PortalStructureChangedError,
        ):
            manual_review = (
                self._checkpoints.mark_manual_review(
                    execution.execution_id,
                    error_info,
                )
            )

            return StepExecutionResult(
                execution=manual_review,
                outcome=(
                    StepExecutionOutcome.MANUAL_REVIEW
                ),
                step=step,
                message=str(error),
            )

        failed = self._checkpoints.mark_failed(
            execution.execution_id,
            error_info,
        )

        return StepExecutionResult(
            execution=failed,
            outcome=StepExecutionOutcome.FAILED,
            step=step,
            message=str(error),
        )

    def _handle_unknown_error(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        error: Exception,
    ) -> StepExecutionResult:
        """
        Un error no clasificado se envía a revisión manual.

        No se reintenta automáticamente porque no existe evidencia
        suficiente para garantizar que repetir la acción sea seguro.
        """

        error_info = ExecutionErrorInfo(
            code="UNKNOWN_STEP_EXECUTION_ERROR",
            category=ErrorCategory.UNKNOWN,
            message=(
                f"{type(error).__name__}: {error}"
            ),
            retryable=False,
            metadata={
                "step": step.value,
            },
        )

        self._safe_recover()

        manual_review = (
            self._checkpoints.mark_manual_review(
                execution.execution_id,
                error_info,
            )
        )

        return StepExecutionResult(
            execution=manual_review,
            outcome=StepExecutionOutcome.MANUAL_REVIEW,
            step=step,
            message=error_info.message,
        )

    def _mark_ambiguous(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        verification: PortalStepVerification,
    ) -> StepExecutionResult:
        """
        Detiene la automatización cuando no se puede determinar si una
        etapa está aplicada.
        """

        error_info = ExecutionErrorInfo(
            code="AMBIGUOUS_PORTAL_STEP_STATE",
            category=ErrorCategory.PORTAL_STRUCTURE,
            message=(
                verification.message
                or (
                    "No fue posible determinar si la etapa "
                    "está aplicada en el portal."
                )
            ),
            retryable=False,
            metadata={
                "step": step.value,
                **dict(verification.metadata),
            },
        )

        manual_review = (
            self._checkpoints.mark_manual_review(
                execution.execution_id,
                error_info,
            )
        )

        return StepExecutionResult(
            execution=manual_review,
            outcome=StepExecutionOutcome.MANUAL_REVIEW,
            step=step,
            message=error_info.message,
        )

    def _finish_if_ready(
        self,
        execution: ContractExecution,
    ) -> StepExecutionResult:
        """
        Finaliza la ejecución cuando la última etapa operativa ya fue
        confirmada.
        """

        if (
            execution.status is ExecutionStatus.RUNNING
            and execution.last_completed_step
            is ContractStep.ADDITIONAL_DATES_LINKED
        ):
            completed = self._checkpoints.finish(
                execution.execution_id
            )

            return StepExecutionResult(
                execution=completed,
                outcome=StepExecutionOutcome.COMPLETED,
                step=ContractStep.COMPLETED,
                message=(
                    "Todas las etapas fueron confirmadas."
                ),
            )

        return StepExecutionResult(
            execution=execution,
            outcome=StepExecutionOutcome.NO_ACTION,
            step=None,
            message=(
                "No existe una etapa pendiente ejecutable."
            ),
        )

    def _safe_recover(self) -> None:
        """
        Intenta recuperar el navegador sin reemplazar el error original.
        """

        try:
            self._portal.recover()
        except Exception:
=======
from __future__ import annotations

from uuid import UUID

from application.dto import (
    PortalStepVerification,
    PortalVerificationStatus,
    StepExecutionOutcome,
    StepExecutionResult,
)
from application.ports import ContractPortal
from application.workflow.checkpoint_service import (
    ExecutionCheckpointService,
)
from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.errors import (
    PortalAlreadyExistsError,
    PortalAutomationError,
    PortalStructureChangedError,
)
from domain.models import (
    ContractData,
    ContractExecution,
    ExecutionErrorInfo,
)


class StepExecutor:
    """
    Ejecuta una etapa contractual de forma persistente e idempotente.

    Responsabilidades:

    1. Recuperar el checkpoint de la ejecución.
    2. Iniciar un intento cuando corresponda.
    3. Abrir la siguiente etapa.
    4. Ejecutar la acción en el portal.
    5. Verificar la postcondición.
    6. Confirmar el checkpoint.
    7. Clasificar y persistir errores.
    8. Reconciliar etapas interrumpidas.
    """

    TERMINAL_STATUSES: frozenset[ExecutionStatus] = frozenset(
        {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.ALREADY_EXISTS,
            ExecutionStatus.MANUAL_REVIEW,
            ExecutionStatus.FAILED,
        }
    )

    STARTABLE_STATUSES: frozenset[ExecutionStatus] = frozenset(
        {
            ExecutionStatus.PENDING,
            ExecutionStatus.RETRY_PENDING,
        }
    )

    def __init__(
        self,
        *,
        portal: ContractPortal,
        checkpoints: ExecutionCheckpointService,
        portal_profile: str | None = None,
    ) -> None:
        self._portal = portal
        self._checkpoints = checkpoints
        self._portal_profile = portal_profile

    def execute_next(
        self,
        *,
        execution_id: UUID,
        contract: ContractData,
    ) -> StepExecutionResult:
        """
        Ejecuta o reconcilia una única etapa.

        Una llamada a este método procesa como máximo una etapa.
        """

        execution = self._checkpoints.get(
            execution_id
        )

        if execution.status in self.TERMINAL_STATUSES:
            return StepExecutionResult(
                execution=execution,
                outcome=StepExecutionOutcome.NO_ACTION,
                step=None,
                message=(
                    "La ejecución no admite acciones automáticas "
                    f"desde el estado {execution.status.value}."
                ),
            )

        if execution.status in self.STARTABLE_STATUSES:
            execution = self._checkpoints.start_attempt(
                execution.execution_id,
                portal_profile=self._portal_profile,
            )

        resume_state = self._checkpoints.get_resume_state(
            contract_number=contract.contract_number,
            dependency=contract.dependency,
        )

        if resume_state is None:
            raise RuntimeError(
                "No fue posible recuperar el checkpoint del contrato "
                "después de iniciar el intento."
            )

        if resume_state.step is None:
            return self._finish_if_ready(
                resume_state.execution
            )

        if resume_state.requires_reconciliation:
            return self._reconcile_open_step(
                execution=resume_state.execution,
                step=resume_state.step,
                contract=contract,
            )

        opened_execution = (
            self._checkpoints.begin_next_step(
                execution.execution_id
            )
        )

        step = opened_execution.current_step

        if step is None:
            raise RuntimeError(
                "El servicio de checkpoints no dejó una etapa abierta."
            )

        # ContractData ya fue construido y validado antes de llegar
        # al portal. INPUT_VALIDATED no necesita Selenium.
        if step is ContractStep.INPUT_VALIDATED:
            confirmed_execution = (
                self._checkpoints.confirm_current_step(
                    execution.execution_id,
                    confirmed_step=step,
                )
            )

            return StepExecutionResult(
                execution=confirmed_execution,
                outcome=(
                    StepExecutionOutcome.STEP_CONFIRMED
                ),
                step=step,
                message=(
                    "Los datos de entrada fueron validados."
                ),
            )

        return self._execute_open_step(
            execution=opened_execution,
            step=step,
            contract=contract,
        )

    def _reconcile_open_step(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        contract: ContractData,
    ) -> StepExecutionResult:
        """
        Determina qué ocurrió con una etapa que quedó abierta.

        La etapa pudo haber sido aplicada en el portal antes de que el
        proceso se interrumpiera. Por ello primero se verifica y no se
        repite automáticamente.
        """

        try:
            verification = self._portal.verify_step(
                step,
                contract,
            )

        except PortalAlreadyExistsError as error:
            return self._mark_already_exists(
                execution=execution,
                step=step,
                error=error,
            )

        except PortalAutomationError as error:
            return self._handle_portal_error(
                execution=execution,
                step=step,
                error=error,
            )

        except Exception as error:
            return self._handle_unknown_error(
                execution=execution,
                step=step,
                error=error,
            )

        if (
            verification.status
            is PortalVerificationStatus.CONFIRMED
        ):
            confirmed_execution = (
                self._checkpoints.confirm_current_step(
                    execution.execution_id,
                    confirmed_step=step,
                )
            )

            return StepExecutionResult(
                execution=confirmed_execution,
                outcome=(
                    StepExecutionOutcome.STEP_RECONCILED
                ),
                step=step,
                message=(
                    verification.message
                    or (
                        "La etapa interrumpida ya estaba "
                        "aplicada en el portal."
                    )
                ),
            )

        if (
            verification.status
            is PortalVerificationStatus.NOT_APPLIED
        ):
            return self._execute_open_step(
                execution=execution,
                step=step,
                contract=contract,
            )

        return self._mark_ambiguous(
            execution=execution,
            step=step,
            verification=verification,
        )

    def _execute_open_step(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        contract: ContractData,
    ) -> StepExecutionResult:
        """
        Ejecuta una etapa abierta y verifica su postcondición.
        """

        try:
            self._portal.execute_step(
                step,
                contract,
            )

            verification = self._portal.verify_step(
                step,
                contract,
            )

            if (
                verification.status
                is PortalVerificationStatus.CONFIRMED
            ):
                confirmed_execution = (
                    self._checkpoints.confirm_current_step(
                        execution.execution_id,
                        confirmed_step=step,
                    )
                )

                return StepExecutionResult(
                    execution=confirmed_execution,
                    outcome=(
                        StepExecutionOutcome.STEP_CONFIRMED
                    ),
                    step=step,
                    message=(
                        verification.message
                        or "La etapa fue confirmada."
                    ),
                )

            if (
                verification.status
                is PortalVerificationStatus.AMBIGUOUS
            ):
                return self._mark_ambiguous(
                    execution=execution,
                    step=step,
                    verification=verification,
                )

            error_info = ExecutionErrorInfo(
                code="STEP_POSTCONDITION_NOT_CONFIRMED",
                category=ErrorCategory.PORTAL_VALIDATION,
                message=(
                    verification.message
                    or (
                        "La acción fue ejecutada, pero el portal "
                        "no confirmó su postcondición."
                    )
                ),
                retryable=True,
                metadata={
                    "step": step.value,
                    **dict(verification.metadata),
                },
            )

            retry_pending = (
                self._checkpoints.mark_retry_pending(
                    execution.execution_id,
                    error_info,
                )
            )

            self._safe_recover()

            return StepExecutionResult(
                execution=retry_pending,
                outcome=StepExecutionOutcome.RETRY_PENDING,
                step=step,
                message=error_info.message,
            )

        except PortalAlreadyExistsError as error:
            return self._mark_already_exists(
                execution=execution,
                step=step,
                error=error,
            )

        except PortalAutomationError as error:
            return self._handle_portal_error(
                execution=execution,
                step=step,
                error=error,
            )

        except Exception as error:
            return self._handle_unknown_error(
                execution=execution,
                step=step,
                error=error,
            )

    def _mark_already_exists(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        error: PortalAlreadyExistsError,
    ) -> StepExecutionResult:
        """
        Finaliza la ejecución porque el portal confirmó que el contrato
        ya estaba registrado.
        """

        already_exists = (
            self._checkpoints.mark_already_exists(
                execution.execution_id,
                message=str(error),
            )
        )

        return StepExecutionResult(
            execution=already_exists,
            outcome=(
                StepExecutionOutcome.ALREADY_EXISTS
            ),
            step=step,
            message=str(error),
        )

    def _handle_portal_error(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        error: PortalAutomationError,
    ) -> StepExecutionResult:
        """
        Convierte una excepción conocida del portal en un error
        persistible.
        """

        error_info = ExecutionErrorInfo(
            code=error.code,
            category=error.category,
            message=str(error),
            retryable=error.retryable,
            metadata={
                "step": step.value,
                **error.metadata,
            },
        )

        self._safe_recover()

        if error.retryable:
            retry_pending = (
                self._checkpoints.mark_retry_pending(
                    execution.execution_id,
                    error_info,
                )
            )

            return StepExecutionResult(
                execution=retry_pending,
                outcome=StepExecutionOutcome.RETRY_PENDING,
                step=step,
                message=str(error),
            )

        if isinstance(
            error,
            PortalStructureChangedError,
        ):
            manual_review = (
                self._checkpoints.mark_manual_review(
                    execution.execution_id,
                    error_info,
                )
            )

            return StepExecutionResult(
                execution=manual_review,
                outcome=(
                    StepExecutionOutcome.MANUAL_REVIEW
                ),
                step=step,
                message=str(error),
            )

        failed = self._checkpoints.mark_failed(
            execution.execution_id,
            error_info,
        )

        return StepExecutionResult(
            execution=failed,
            outcome=StepExecutionOutcome.FAILED,
            step=step,
            message=str(error),
        )

    def _handle_unknown_error(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        error: Exception,
    ) -> StepExecutionResult:
        """
        Un error no clasificado se envía a revisión manual.

        No se reintenta automáticamente porque no existe evidencia
        suficiente para garantizar que repetir la acción sea seguro.
        """

        error_info = ExecutionErrorInfo(
            code="UNKNOWN_STEP_EXECUTION_ERROR",
            category=ErrorCategory.UNKNOWN,
            message=(
                f"{type(error).__name__}: {error}"
            ),
            retryable=False,
            metadata={
                "step": step.value,
            },
        )

        self._safe_recover()

        manual_review = (
            self._checkpoints.mark_manual_review(
                execution.execution_id,
                error_info,
            )
        )

        return StepExecutionResult(
            execution=manual_review,
            outcome=StepExecutionOutcome.MANUAL_REVIEW,
            step=step,
            message=error_info.message,
        )

    def _mark_ambiguous(
        self,
        *,
        execution: ContractExecution,
        step: ContractStep,
        verification: PortalStepVerification,
    ) -> StepExecutionResult:
        """
        Detiene la automatización cuando no se puede determinar si una
        etapa está aplicada.
        """

        error_info = ExecutionErrorInfo(
            code="AMBIGUOUS_PORTAL_STEP_STATE",
            category=ErrorCategory.PORTAL_STRUCTURE,
            message=(
                verification.message
                or (
                    "No fue posible determinar si la etapa "
                    "está aplicada en el portal."
                )
            ),
            retryable=False,
            metadata={
                "step": step.value,
                **dict(verification.metadata),
            },
        )

        manual_review = (
            self._checkpoints.mark_manual_review(
                execution.execution_id,
                error_info,
            )
        )

        return StepExecutionResult(
            execution=manual_review,
            outcome=StepExecutionOutcome.MANUAL_REVIEW,
            step=step,
            message=error_info.message,
        )

    def _finish_if_ready(
        self,
        execution: ContractExecution,
    ) -> StepExecutionResult:
        """
        Finaliza la ejecución cuando la última etapa operativa ya fue
        confirmada.
        """

        if (
            execution.status is ExecutionStatus.RUNNING
            and execution.last_completed_step
            is ContractStep.ADDITIONAL_DATES_LINKED
        ):
            completed = self._checkpoints.finish(
                execution.execution_id
            )

            return StepExecutionResult(
                execution=completed,
                outcome=StepExecutionOutcome.COMPLETED,
                step=ContractStep.COMPLETED,
                message=(
                    "Todas las etapas fueron confirmadas."
                ),
            )

        return StepExecutionResult(
            execution=execution,
            outcome=StepExecutionOutcome.NO_ACTION,
            step=None,
            message=(
                "No existe una etapa pendiente ejecutable."
            ),
        )

    def _safe_recover(self) -> None:
        """
        Intenta recuperar el navegador sin reemplazar el error original.
        """

        try:
            self._portal.recover()
        except Exception:
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
            pass