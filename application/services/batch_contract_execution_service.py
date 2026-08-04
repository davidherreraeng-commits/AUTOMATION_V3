from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Lock
from uuid import UUID

from application.dto.batch_contract_execution import (
    BatchContractExecutionIssue,
    BatchContractExecutionPreflight,
    BatchContractExecutionResult,
)
from application.ports.batch_repository import BatchRepository
from application.ports.contract_executor import ContractExecutor
from application.ports.portal_credential_repository import (
    PortalCredentialRepository,
)
from application.workflow.checkpoint_service import ExecutionCheckpointService
from domain.enums import ExecutionStatus
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.errors.batch_contract_execution_errors import (
    BatchContractExecutionBlockedError,
    BatchContractExecutionConfirmationError,
    BatchContractExecutionIdentityError,
    BatchContractExecutionInProgressError,
    BatchContractExecutionStateError,
    BatchContractItemNotFoundError,
)
from domain.errors.batch_errors import BatchNotFoundError
from domain.errors.portal_credential_errors import PortalCredentialError
from domain.errors.portal_errors import PortalAutomationError
from domain.models import ContractExecution
from domain.models.contract_batch import BatchContract, ContractBatch


class BatchContractExecutionService:
    """Ejecuta un contrato seleccionado sin habilitar el lote masivo.

    La coordinación conserva una sola sesión Selenium por invocación,
    persiste checkpoints mediante ``ExecuteContractInSession`` y refleja
    el resultado en el contrato del lote.

    El bloqueo de proceso es deliberadamente global porque el adaptador
    6C14B admite una sola sesión contractual de navegador por proceso.
    """

    EXECUTABLE_BATCH_STATUSES = frozenset(
        {BatchStatus.READY, BatchStatus.PROCESSING}
    )
    EXECUTABLE_ITEM_STATUSES = frozenset(
        {BatchContractStatus.PENDING, BatchContractStatus.PROCESSING}
    )
    RESUMABLE_EXECUTION_STATUSES = frozenset(
        {
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.RETRY_PENDING,
        }
    )
    TERMINAL_ITEM_STATUSES = frozenset(
        {
            BatchContractStatus.COMPLETED,
            BatchContractStatus.FAILED,
            BatchContractStatus.MANUAL_REVIEW,
        }
    )

    def __init__(
        self,
        *,
        batches: BatchRepository,
        credentials: PortalCredentialRepository,
        checkpoints: ExecutionCheckpointService,
        executor: ContractExecutor | None,
        execution_enabled: bool,
        credential_max_age_hours: int = 24,
        reject_unit_test_values: bool = True,
    ) -> None:
        if credential_max_age_hours <= 0:
            raise ValueError(
                "La vigencia de las credenciales debe ser positiva."
            )

        self._batches = batches
        self._credentials = credentials
        self._checkpoints = checkpoints
        self._executor = executor
        self._execution_enabled = bool(execution_enabled)
        self._credential_max_age = timedelta(
            hours=credential_max_age_hours
        )
        self._reject_unit_test_values = bool(reject_unit_test_values)
        self._active_lock = Lock()
        self._active_items: set[tuple[UUID, UUID]] = set()

    def preflight(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> BatchContractExecutionPreflight:
        batch, item = self._get_context(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        issues: list[BatchContractExecutionIssue] = []

        if not self._execution_enabled:
            issues.append(
                BatchContractExecutionIssue(
                    code="EXECUTION_DISABLED",
                    message=(
                        "La escritura real está deshabilitada. Active "
                        "RPA_BATCH_EXECUTION_ENABLED únicamente durante "
                        "una prueba controlada."
                    ),
                )
            )

        if self._executor is None:
            issues.append(
                BatchContractExecutionIssue(
                    code="CONTRACT_EXECUTOR_UNAVAILABLE",
                    message=(
                        "El ejecutor contractual 6C14B no está disponible "
                        "porque falta su composición o el cifrado Fernet."
                    ),
                )
            )

        if batch.status not in self.EXECUTABLE_BATCH_STATUSES:
            issues.append(
                BatchContractExecutionIssue(
                    code="BATCH_STATE_NOT_EXECUTABLE",
                    message=(
                        "El lote debe estar en READY o PROCESSING para "
                        "ejecutar un contrato individual. Estado actual: "
                        f"{batch.status.value}."
                    ),
                )
            )

        if item.status not in self.EXECUTABLE_ITEM_STATUSES:
            issues.append(
                BatchContractExecutionIssue(
                    code="ITEM_STATE_NOT_EXECUTABLE",
                    message=(
                        "El contrato seleccionado ya está en un estado "
                        f"terminal: {item.status.value}."
                    ),
                )
            )

        other_processing = tuple(
            candidate
            for candidate in batch.contracts
            if candidate.item_id != item.item_id
            and candidate.status is BatchContractStatus.PROCESSING
        )
        if other_processing:
            issues.append(
                BatchContractExecutionIssue(
                    code="ANOTHER_ITEM_PROCESSING",
                    message=(
                        "Otro contrato del lote está pendiente de finalizar "
                        "o reanudar. Complete ese contrato antes de iniciar "
                        "uno diferente."
                    ),
                )
            )

        active_in_process, another_active = self._active_state(
            batch_id=batch_id,
            item_id=item_id,
        )
        if active_in_process:
            issues.append(
                BatchContractExecutionIssue(
                    code="ITEM_ACTIVE_IN_PROCESS",
                    message=(
                        "Este contrato ya tiene una ejecución activa en "
                        "el proceso actual."
                    ),
                )
            )
        elif another_active:
            issues.append(
                BatchContractExecutionIssue(
                    code="BROWSER_SESSION_BUSY",
                    message=(
                        "Ya existe otra sesión contractual de Chrome activa "
                        "en el proceso actual."
                    ),
                )
            )

        credential = self._credentials.find_by_dependency(
            batch.dependency
        )
        credentials_configured = credential is not None
        credentials_recently_tested = False

        if credential is None:
            issues.append(
                BatchContractExecutionIssue(
                    code="CREDENTIALS_NOT_CONFIGURED",
                    message=(
                        "No hay credenciales de Gestión Transparente "
                        "configuradas para la dependencia."
                    ),
                )
            )
        elif credential.last_test_success is not True:
            issues.append(
                BatchContractExecutionIssue(
                    code="CREDENTIALS_NOT_VERIFIED",
                    message=(
                        "Las credenciales no tienen una prueba exitosa "
                        "vigente."
                    ),
                )
            )
        elif credential.last_tested_at is None:
            issues.append(
                BatchContractExecutionIssue(
                    code="CREDENTIALS_TEST_DATE_MISSING",
                    message=(
                        "No fue posible determinar cuándo se probaron "
                        "las credenciales."
                    ),
                )
            )
        else:
            tested_at = credential.last_tested_at
            if tested_at.tzinfo is None:
                tested_at = tested_at.replace(tzinfo=UTC)
            credentials_recently_tested = (
                datetime.now(UTC) - tested_at.astimezone(UTC)
                <= self._credential_max_age
            )
            if not credentials_recently_tested:
                issues.append(
                    BatchContractExecutionIssue(
                        code="CREDENTIALS_TEST_EXPIRED",
                        message=(
                            "La última prueba exitosa de credenciales "
                            "expiró. Vuelva a probarlas antes de escribir."
                        ),
                    )
                )

        contract = item.contract
        if not contract.secop_url:
            issues.append(
                BatchContractExecutionIssue(
                    code="SECOP_URL_REQUIRED",
                    message=(
                        "El Enlace Proceso SECOP II es obligatorio para "
                        "la ejecución real."
                    ),
                )
            )
        if not contract.budget.budget_register_number:
            issues.append(
                BatchContractExecutionIssue(
                    code="BUDGET_REGISTER_REQUIRED",
                    message=(
                        "El No. RP es obligatorio para la ejecución real."
                    ),
                )
            )
        if contract.budget.gross_total <= Decimal("0"):
            issues.append(
                BatchContractExecutionIssue(
                    code="GROSS_TOTAL_REQUIRED",
                    message=(
                        "Total Bruto debe ser mayor que cero y no puede "
                        "completarse usando Valor."
                    ),
                )
            )

        if self._reject_unit_test_values and (
            contract.amount <= Decimal("1")
            or contract.budget.gross_total <= Decimal("1")
        ):
            issues.append(
                BatchContractExecutionIssue(
                    code="TEST_VALUES_DETECTED",
                    message=(
                        "El contrato contiene valores unitarios de prueba "
                        "y no puede enviarse al portal real."
                    ),
                )
            )

        execution = self._existing_execution(item)
        resumable = (
            (
                execution is not None
                and execution.status in self.RESUMABLE_EXECUTION_STATUSES
            )
            or (
                execution is None
                and item.status is BatchContractStatus.PROCESSING
            )
        )
        if execution is not None and not resumable:
            issues.append(
                BatchContractExecutionIssue(
                    code="EXECUTION_TERMINAL",
                    message=(
                        "El checkpoint del contrato está en estado terminal "
                        f"{execution.status.value}; no se repetirá la escritura."
                    ),
                )
            )

        return BatchContractExecutionPreflight(
            batch=batch,
            item=item,
            required_confirmation=self.required_confirmation(item),
            execution_enabled=self._execution_enabled,
            executor_available=self._executor is not None,
            credentials_configured=credentials_configured,
            credentials_recently_tested=credentials_recently_tested,
            active_in_process=active_in_process,
            execution=execution,
            resumable=resumable,
            checked_at=datetime.now(UTC),
            issues=tuple(issues),
        )

    def execute(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        execution_id: UUID | None = None,
    ) -> BatchContractExecutionResult:
        preflight = self.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        blocking = tuple(
            (issue.code, issue.message)
            for issue in preflight.issues
            if issue.blocking
        )
        if blocking:
            raise BatchContractExecutionBlockedError(blocking)

        required = preflight.required_confirmation
        if self._confirmation_identity(confirmation) != (
            self._confirmation_identity(required)
        ):
            raise BatchContractExecutionConfirmationError(required)

        selected_execution_id = self._resolve_execution_id(
            existing=preflight.execution,
            requested=execution_id,
        )

        key = (batch_id, item_id)
        self._acquire(key)

        try:
            batch, item = self._prepare_item(
                batch=preflight.batch,
                item=preflight.item,
                dependency=dependency,
            )

            executor = self._executor
            if executor is None:
                raise BatchContractExecutionStateError(
                    "El ejecutor contractual dejó de estar disponible."
                )

            try:
                processing = executor.execute(
                    contract=item.contract,
                    execution_id=selected_execution_id,
                )
            except Exception as error:
                return self._result_from_escaped_error(
                    batch=batch,
                    item=item,
                    dependency=dependency,
                    error=error,
                )

            execution = processing.execution
            item_status = self._item_status_for_execution(
                execution.status
            )
            operational_message = self._message_for_execution(execution)
            updated = self._batches.update_contract_status(
                batch.batch_id,
                item.item_id,
                dependency=dependency,
                status=item_status,
                message=operational_message,
            )
            updated = self._finish_batch_if_ready(
                updated,
                dependency=dependency,
            )
            updated_item = self._find_item(updated, item.item_id)
            error_code, technical_detail = self._execution_error_details(
                execution
            )

            return BatchContractExecutionResult(
                batch=updated,
                item=updated_item,
                required_confirmation=required,
                active_in_process=False,
                execution=execution,
                transition_count=len(processing.transitions),
                success=execution.status in {
                    ExecutionStatus.COMPLETED,
                    ExecutionStatus.ALREADY_EXISTS,
                },
                resumable=(
                    execution.status
                    in self.RESUMABLE_EXECUTION_STATUSES
                ),
                retry_pending=(
                    execution.status is ExecutionStatus.RETRY_PENDING
                ),
                requires_manual_review=(
                    execution.status is ExecutionStatus.MANUAL_REVIEW
                ),
                operational_message=operational_message,
                error_code=error_code,
                technical_detail=technical_detail,
                transitions=processing.transitions,
            )
        finally:
            self._release(key)

    def status(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> BatchContractExecutionResult:
        batch, item = self._get_context(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        execution = self._existing_execution(item)
        active, _ = self._active_state(
            batch_id=batch_id,
            item_id=item_id,
        )
        error_code, technical_detail = self._execution_error_details(
            execution
        )

        if item.last_message:
            message = item.last_message
        elif execution is None:
            message = "El contrato todavía no tiene un checkpoint."
        else:
            message = self._message_for_execution(execution)

        return BatchContractExecutionResult(
            batch=batch,
            item=item,
            required_confirmation=self.required_confirmation(item),
            active_in_process=active,
            execution=execution,
            transition_count=0,
            success=(
                execution is not None
                and execution.status in {
                    ExecutionStatus.COMPLETED,
                    ExecutionStatus.ALREADY_EXISTS,
                }
            ),
            resumable=(
                (
                    execution is not None
                    and execution.status
                    in self.RESUMABLE_EXECUTION_STATUSES
                )
                or (
                    execution is None
                    and item.status is BatchContractStatus.PROCESSING
                )
            ),
            retry_pending=(
                (
                    execution is not None
                    and execution.status
                    in self.RESUMABLE_EXECUTION_STATUSES
                )
                or (
                    execution is None
                    and item.status is BatchContractStatus.PROCESSING
                )
            ),
            requires_manual_review=(
                execution is not None
                and execution.status is ExecutionStatus.MANUAL_REVIEW
            ),
            operational_message=message,
            error_code=error_code,
            technical_detail=technical_detail,
        )

    @staticmethod
    def required_confirmation(item: BatchContract) -> str:
        return f"EJECUTAR CONTRATO {item.contract.contract_number}"

    def _prepare_item(
        self,
        *,
        batch: ContractBatch,
        item: BatchContract,
        dependency: str,
    ) -> tuple[ContractBatch, BatchContract]:
        if batch.status is BatchStatus.READY:
            batch = self._batches.claim_for_processing(
                batch.batch_id,
                dependency=dependency,
            )
            item = self._find_item(batch, item.item_id)
        elif batch.status is not BatchStatus.PROCESSING:
            raise BatchContractExecutionStateError(
                "El lote dejó de estar disponible para ejecución."
            )

        if item.status is BatchContractStatus.PENDING:
            batch = self._batches.update_contract_status(
                batch.batch_id,
                item.item_id,
                dependency=dependency,
                status=BatchContractStatus.PROCESSING,
                message="Contrato en ejecución controlada.",
            )
            item = self._find_item(batch, item.item_id)
        elif item.status is not BatchContractStatus.PROCESSING:
            raise BatchContractExecutionStateError(
                "El contrato dejó de estar disponible para ejecución."
            )

        return batch, item

    def _result_from_escaped_error(
        self,
        *,
        batch: ContractBatch,
        item: BatchContract,
        dependency: str,
        error: Exception,
    ) -> BatchContractExecutionResult:
        retryable = self._is_retryable_escaped_error(error)
        status = (
            BatchContractStatus.PROCESSING
            if retryable
            else BatchContractStatus.FAILED
        )
        operational_message = (
            "No fue posible completar la sesión del portal. Corrija la "
            "causa indicada y reanude el mismo contrato."
            if retryable
            else "La ejecución se detuvo por un error no recuperable."
        )
        updated = self._batches.update_contract_status(
            batch.batch_id,
            item.item_id,
            dependency=dependency,
            status=status,
            message=operational_message,
        )
        if status is not BatchContractStatus.PROCESSING:
            updated = self._finish_batch_if_ready(
                updated,
                dependency=dependency,
            )
        updated_item = self._find_item(updated, item.item_id)
        execution = self._existing_execution(updated_item)

        return BatchContractExecutionResult(
            batch=updated,
            item=updated_item,
            required_confirmation=self.required_confirmation(updated_item),
            active_in_process=False,
            execution=execution,
            transition_count=0,
            success=False,
            resumable=retryable,
            retry_pending=retryable,
            requires_manual_review=False,
            operational_message=operational_message,
            error_code=str(
                getattr(error, "code", type(error).__name__)
            ).strip(),
            technical_detail=(
                f"{type(error).__name__}: {str(error).strip()}"
            ),
        )

    def _finish_batch_if_ready(
        self,
        batch: ContractBatch,
        *,
        dependency: str,
    ) -> ContractBatch:
        statuses = {item.status for item in batch.contracts}
        if BatchContractStatus.PENDING in statuses:
            return batch
        if BatchContractStatus.PROCESSING in statuses:
            return batch

        final_status = (
            BatchStatus.COMPLETED
            if statuses == {BatchContractStatus.COMPLETED}
            else BatchStatus.COMPLETED_WITH_ERRORS
        )
        return self._batches.finish_processing(
            batch.batch_id,
            dependency=dependency,
            status=final_status,
        )

    def _get_context(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> tuple[ContractBatch, BatchContract]:
        batch = self._batches.get_by_id(
            batch_id,
            dependency=dependency,
        )
        if batch is None:
            raise BatchNotFoundError(str(batch_id))
        return batch, self._find_item(batch, item_id)

    @staticmethod
    def _find_item(
        batch: ContractBatch,
        item_id: UUID,
    ) -> BatchContract:
        for item in batch.contracts:
            if item.item_id == item_id:
                return item
        raise BatchContractItemNotFoundError(
            batch_id=batch.batch_id,
            item_id=item_id,
        )

    def _existing_execution(
        self,
        item: BatchContract,
    ) -> ContractExecution | None:
        resume = self._checkpoints.get_resume_state(
            contract_number=item.contract.contract_number,
            dependency=item.contract.dependency,
        )
        if resume is None:
            return None
        return resume.execution

    @staticmethod
    def _resolve_execution_id(
        *,
        existing: ContractExecution | None,
        requested: UUID | None,
    ) -> UUID | None:
        if requested is None:
            return existing.execution_id if existing is not None else None
        if existing is None:
            raise BatchContractExecutionIdentityError(
                "El execution_id recibido no corresponde a un checkpoint "
                "existente del contrato seleccionado."
            )
        if requested != existing.execution_id:
            raise BatchContractExecutionIdentityError(
                "El execution_id recibido pertenece a otra ejecución."
            )
        return requested

    @staticmethod
    def _item_status_for_execution(
        status: ExecutionStatus,
    ) -> BatchContractStatus:
        if status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.ALREADY_EXISTS,
        }:
            return BatchContractStatus.COMPLETED
        if status is ExecutionStatus.MANUAL_REVIEW:
            return BatchContractStatus.MANUAL_REVIEW
        if status is ExecutionStatus.FAILED:
            return BatchContractStatus.FAILED
        return BatchContractStatus.PROCESSING

    @staticmethod
    def _message_for_execution(
        execution: ContractExecution,
    ) -> str:
        messages = {
            ExecutionStatus.PENDING: (
                "El checkpoint fue creado y está pendiente de iniciar."
            ),
            ExecutionStatus.RUNNING: (
                "La ejecución quedó abierta y debe reconciliarse."
            ),
            ExecutionStatus.RETRY_PENDING: (
                "El portal presentó un error recuperable. Reanude el "
                "mismo contrato."
            ),
            ExecutionStatus.MANUAL_REVIEW: (
                "La ejecución requiere revisión manual antes de continuar."
            ),
            ExecutionStatus.ALREADY_EXISTS: (
                "Gestión Transparente confirmó que el contrato ya existía."
            ),
            ExecutionStatus.COMPLETED: (
                "El contrato finalizó todas las etapas confirmadas."
            ),
            ExecutionStatus.FAILED: (
                "La ejecución terminó con un error no recuperable."
            ),
        }
        return messages[execution.status]

    @staticmethod
    def _execution_error_details(
        execution: ContractExecution | None,
    ) -> tuple[str | None, str | None]:
        if execution is None or execution.last_error is None:
            return None, None
        error = execution.last_error
        return error.code, f"{error.code}: {error.message}"

    @staticmethod
    def _is_retryable_escaped_error(error: Exception) -> bool:
        if isinstance(error, PortalAutomationError):
            return bool(error.retryable)
        if isinstance(error, PortalCredentialError):
            return True
        return type(error).__name__ == "ContractPortalSessionBusyError"

    def _active_state(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
    ) -> tuple[bool, bool]:
        key = (batch_id, item_id)
        with self._active_lock:
            return key in self._active_items, bool(
                self._active_items and key not in self._active_items
            )

    def _acquire(self, key: tuple[UUID, UUID]) -> None:
        with self._active_lock:
            if self._active_items:
                active_batch_id, active_item_id = next(
                    iter(self._active_items)
                )
                raise BatchContractExecutionInProgressError(
                    batch_id=active_batch_id,
                    item_id=active_item_id,
                )
            self._active_items.add(key)

    def _release(self, key: tuple[UUID, UUID]) -> None:
        with self._active_lock:
            self._active_items.discard(key)

    @staticmethod
    def _confirmation_identity(value: object) -> str:
        return " ".join(str(value).split()).casefold()
