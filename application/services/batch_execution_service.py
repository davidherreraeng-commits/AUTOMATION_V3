from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import UUID

from application.dto.batch_execution import (
    BatchExecutionPreflight,
    BatchExecutionPreflightIssue,
)
from application.ports.batch_execution_runner import (
    BatchExecutionCallbacks,
    BatchExecutionRunner,
)
from application.ports.batch_repository import BatchRepository
from application.services.contract_value_policy import ContractValuePolicy
from application.ports.portal_credential_repository import (
    PortalCredentialRepository,
)
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.errors.batch_errors import BatchNotFoundError
from domain.errors.batch_execution_errors import BatchExecutionBlockedError
from domain.models.contract_batch import ContractBatch


class BatchExecutionService:
    """Controla preflight, exclusión y ejecución en segundo plano.

    El servicio no conoce Selenium. La ejecución concreta se delega al
    puerto BatchExecutionRunner, lo que permite probar el ciclo de vida
    sin abrir un navegador ni modificar el portal.
    """

    def __init__(
        self,
        *,
        batches: BatchRepository,
        credentials: PortalCredentialRepository,
        runner: BatchExecutionRunner,
        execution_enabled: bool,
        cipher_configured: bool,
        credential_max_age_hours: int = 24,
        reject_unit_test_values: bool = True,
        allowed_nominal_value_contracts: tuple[str, ...] = (),
        max_workers: int = 2,
    ) -> None:
        if credential_max_age_hours <= 0:
            raise ValueError(
                "La vigencia de la prueba de credenciales debe ser positiva."
            )
        if max_workers <= 0:
            raise ValueError("El número de workers debe ser positivo.")

        self._batches = batches
        self._credentials = credentials
        self._runner = runner
        self._execution_enabled = bool(execution_enabled)
        self._cipher_configured = bool(cipher_configured)
        self._credential_max_age = timedelta(hours=credential_max_age_hours)
        self._value_policy = ContractValuePolicy(
            reject_nominal_values=reject_unit_test_values,
            allowed_contract_numbers=allowed_nominal_value_contracts,
        )
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="rpa-batch",
        )
        self._futures: dict[UUID, Future[None]] = {}
        self._future_lock = Lock()

    def preflight(
        self,
        *,
        batch_id: UUID,
        dependency: str,
    ) -> BatchExecutionPreflight:
        batch = self._get_batch(batch_id=batch_id, dependency=dependency)
        issues: list[BatchExecutionPreflightIssue] = []

        if not self._execution_enabled:
            issues.append(
                BatchExecutionPreflightIssue(
                    code="EXECUTION_DISABLED",
                    message=(
                        "La ejecución de lotes está deshabilitada. "
                        "Defina RPA_BATCH_EXECUTION_ENABLED=true únicamente "
                        "cuando el adaptador Selenium haya sido validado."
                    ),
                )
            )

        if not self._runner.available:
            issues.append(
                BatchExecutionPreflightIssue(
                    code="RUNNER_UNAVAILABLE",
                    message=(
                        "El ejecutor Selenium de lotes todavía no está "
                        "conectado al flujo de producción."
                    ),
                )
            )

        if batch.status is not BatchStatus.READY:
            issues.append(
                BatchExecutionPreflightIssue(
                    code="BATCH_NOT_READY",
                    message=(
                        "El lote debe estar en estado READY. "
                        f"Estado actual: {batch.status.value}."
                    ),
                )
            )

        active = self._batches.get_processing_by_dependency(dependency)
        active_batch_id = active.batch_id if active is not None else None
        if active is not None and active.batch_id != batch.batch_id:
            issues.append(
                BatchExecutionPreflightIssue(
                    code="DEPENDENCY_BUSY",
                    message=(
                        "Ya existe otro lote en ejecución para esta dependencia: "
                        f"{active.batch_id}."
                    ),
                )
            )

        credential = self._credentials.find_by_dependency(dependency)
        credentials_configured = credential is not None
        credentials_recently_tested = False

        if credential is None:
            issues.append(
                BatchExecutionPreflightIssue(
                    code="CREDENTIALS_NOT_CONFIGURED",
                    message=(
                        "No hay credenciales de Gestión Transparente "
                        "configuradas para la dependencia."
                    ),
                )
            )
        else:
            if credential.last_test_success is not True:
                issues.append(
                    BatchExecutionPreflightIssue(
                        code="CREDENTIALS_NOT_VERIFIED",
                        message=(
                            "Las credenciales guardadas no tienen una prueba "
                            "exitosa vigente. Ejecute la prueba desde Configuración."
                        ),
                    )
                )
            elif credential.last_tested_at is None:
                issues.append(
                    BatchExecutionPreflightIssue(
                        code="CREDENTIALS_TEST_DATE_MISSING",
                        message=(
                            "No fue posible determinar cuándo se probaron las "
                            "credenciales del portal."
                        ),
                    )
                )
            else:
                tested_at = credential.last_tested_at
                if tested_at.tzinfo is None:
                    tested_at = tested_at.replace(tzinfo=UTC)
                age = datetime.now(UTC) - tested_at.astimezone(UTC)
                credentials_recently_tested = age <= self._credential_max_age
                if not credentials_recently_tested:
                    issues.append(
                        BatchExecutionPreflightIssue(
                            code="CREDENTIALS_TEST_EXPIRED",
                            message=(
                                "La última prueba exitosa de credenciales expiró. "
                                "Vuelva a probarlas antes de ejecutar el lote."
                            ),
                        )
                    )

        if not self._cipher_configured:
            issues.append(
                BatchExecutionPreflightIssue(
                    code="CIPHER_NOT_CONFIGURED",
                    message=(
                        "El cifrado Fernet no está configurado; no es posible "
                        "descifrar las credenciales del portal."
                    ),
                )
            )

        blocked_nominal_contracts: list[str] = []
        allowed_nominal_contracts: list[str] = []
        for item in batch.contracts:
            assessment = self._value_policy.assess(item.contract)
            if assessment is None:
                continue
            if assessment.blocking:
                blocked_nominal_contracts.append(
                    item.contract.contract_number
                )
            else:
                allowed_nominal_contracts.append(
                    item.contract.contract_number
                )

        if blocked_nominal_contracts:
            preview = ", ".join(blocked_nominal_contracts[:5])
            suffix = (
                ""
                if len(blocked_nominal_contracts) <= 5
                else "…"
            )
            issues.append(
                BatchExecutionPreflightIssue(
                    code="TEST_VALUES_DETECTED",
                    message=(
                        "El lote contiene valores iguales o inferiores a $1 "
                        "sin autorización nominal institucional explícita en: "
                        f"{preview}{suffix}. No se permite enviarlos al portal "
                        "real."
                    ),
                )
            )

        if allowed_nominal_contracts:
            preview = ", ".join(allowed_nominal_contracts[:5])
            suffix = (
                ""
                if len(allowed_nominal_contracts) <= 5
                else "…"
            )
            issues.append(
                BatchExecutionPreflightIssue(
                    code="NOMINAL_VALUE_INSTITUTIONALLY_ALLOWED",
                    message=(
                        "Valor nominal institucional autorizado "
                        f"explícitamente en: {preview}{suffix}. Las demás "
                        "barreras de escritura real permanecen activas."
                    ),
                    blocking=False,
                )
            )

        return BatchExecutionPreflight(
            batch_id=batch.batch_id,
            batch_status=batch.status,
            dependency=batch.dependency,
            runner_name=self._runner.name,
            execution_enabled=self._execution_enabled,
            runner_available=self._runner.available,
            credentials_configured=credentials_configured,
            credentials_recently_tested=credentials_recently_tested,
            active_batch_id=active_batch_id,
            checked_at=datetime.now(UTC),
            issues=tuple(issues),
        )

    def start(
        self,
        *,
        batch_id: UUID,
        dependency: str,
    ) -> ContractBatch:
        preflight = self.preflight(batch_id=batch_id, dependency=dependency)
        if not preflight.can_execute:
            raise BatchExecutionBlockedError(
                tuple(issue.message for issue in preflight.issues if issue.blocking)
            )

        claimed = self._batches.claim_for_processing(
            batch_id,
            dependency=dependency,
        )
        future = self._executor.submit(self._run_claimed, claimed)
        with self._future_lock:
            self._futures[batch_id] = future
        future.add_done_callback(lambda _: self._discard_future(batch_id))
        return claimed

    def get(
        self,
        *,
        batch_id: UUID,
        dependency: str,
    ) -> ContractBatch:
        return self._get_batch(batch_id=batch_id, dependency=dependency)

    def cancel(
        self,
        *,
        batch_id: UUID,
        dependency: str,
    ) -> ContractBatch:
        return self._batches.cancel_ready(batch_id, dependency=dependency)

    def is_active(self, batch_id: UUID) -> bool:
        with self._future_lock:
            future = self._futures.get(batch_id)
            return future is not None and not future.done()

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _run_claimed(self, batch: ContractBatch) -> None:
        callbacks = BatchExecutionCallbacks(
            mark_contract_started=lambda item_id: self._batches.update_contract_status(
                batch.batch_id,
                item_id,
                dependency=batch.dependency,
                status=BatchContractStatus.PROCESSING,
                message="Contrato en ejecución.",
            ),
            mark_contract_finished=lambda item_id, status, message: (
                self._batches.update_contract_status(
                    batch.batch_id,
                    item_id,
                    dependency=batch.dependency,
                    status=status,
                    message=message,
                )
            ),
        )

        try:
            self._runner.run(batch=batch, callbacks=callbacks)
            current = self._get_batch(
                batch_id=batch.batch_id,
                dependency=batch.dependency,
            )
            statuses = {item.status for item in current.contracts}
            if statuses == {BatchContractStatus.COMPLETED}:
                final_status = BatchStatus.COMPLETED
            elif statuses.issubset(
                {
                    BatchContractStatus.COMPLETED,
                    BatchContractStatus.FAILED,
                    BatchContractStatus.MANUAL_REVIEW,
                }
            ):
                final_status = BatchStatus.COMPLETED_WITH_ERRORS
            else:
                final_status = BatchStatus.FAILED
            self._batches.finish_processing(
                batch.batch_id,
                dependency=batch.dependency,
                status=final_status,
            )
        except Exception as error:
            current = self._get_batch(
                batch_id=batch.batch_id,
                dependency=batch.dependency,
            )
            for item in current.contracts:
                if item.status is BatchContractStatus.PROCESSING:
                    self._batches.update_contract_status(
                        batch.batch_id,
                        item.item_id,
                        dependency=batch.dependency,
                        status=BatchContractStatus.FAILED,
                        message=(
                            "La ejecución fue interrumpida por un error del runner: "
                            f"{type(error).__name__}."
                        ),
                    )
            self._batches.finish_processing(
                batch.batch_id,
                dependency=batch.dependency,
                status=BatchStatus.FAILED,
            )

    def _get_batch(self, *, batch_id: UUID, dependency: str) -> ContractBatch:
        batch = self._batches.get_by_id(batch_id, dependency=dependency)
        if batch is None:
            raise BatchNotFoundError(str(batch_id))
        return batch

    def _discard_future(self, batch_id: UUID) -> None:
        with self._future_lock:
            self._futures.pop(batch_id, None)
