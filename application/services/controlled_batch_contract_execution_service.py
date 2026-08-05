from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4

from application.dto.batch_contract_execution import (
    BatchContractExecutionIssue,
    BatchContractExecutionPreflight,
    BatchContractExecutionResult,
)
from application.dto.execution_evidence import (
    ContractExecutionEvidence,
    ExecutionEvidenceEvent,
)
from application.dto.real_write_authorization import (
    IssuedRealWriteAuthorization,
    RealWriteAuthorization,
    RealWriteAuthorizationEvent,
)
from application.ports.contract_executor import ContractExecutor
from application.ports.execution_evidence_repository import (
    ExecutionEvidenceRepository,
)
from application.services.batch_contract_execution_service import (
    BatchContractExecutionService,
)
from application.services.real_write_authorization_service import (
    RealWriteAuthorizationService,
)
from application.services.institutional_test_plan_service import (
    InstitutionalTestPlanService,
)
from domain.enums import (
    ContractStep,
    ExecutionMode,
    ExecutionStatus,
    RealWriteAuthorizationStatus,
    InstitutionalTestPlanStatus,
)
from domain.errors.batch_contract_execution_errors import (
    BatchContractExecutionBlockedError,
    BatchContractExecutionConfirmationError,
    BatchContractExecutionInProgressError,
)
from domain.errors.execution_evidence_errors import (
    ExecutionEvidenceContextError,
    ExecutionEvidenceNotFoundError,
)
from domain.errors.real_write_authorization_errors import (
    RealWriteAuthorizationError,
)
from domain.errors.institutional_test_plan_errors import (
    InstitutionalTestPlanError,
    InstitutionalTestPlanNotFoundError,
)
from domain.models import ContractExecution


class ControlledBatchContractExecutionService:
    """Simula, autoriza y audita la ejecución individual de contratos."""

    AUTHORIZATION_ISSUE_CODES = frozenset(
        {
            "REAL_WRITE_AUTHORIZATION_REQUIRED",
            "REAL_WRITE_AUTHORIZATION_EXPIRED",
            "REAL_WRITE_AUTHORIZATION_ALREADY_CONSUMED",
            "REAL_WRITE_AUTHORIZATION_REVOKED",
        }
    )

    INSTITUTIONAL_PLAN_ISSUE_CODES = frozenset(
        {
            "INSTITUTIONAL_TEST_PLAN_REQUIRED",
            "INSTITUTIONAL_TEST_PLAN_NOT_ARMED",
            "INSTITUTIONAL_TEST_PLAN_DIAGNOSTIC_REQUIRED",
            "INSTITUTIONAL_TEST_PLAN_DRAFT",
            "INSTITUTIONAL_TEST_PLAN_READY",
            "INSTITUTIONAL_TEST_PLAN_CANCELLED",
            "INSTITUTIONAL_TEST_PLAN_CONSUMED",
            "INSTITUTIONAL_TEST_PLAN_EXPIRED",
        }
    )

    DRY_RUN_IGNORED_ISSUES = frozenset(
        {
            "EXECUTION_DISABLED",
            "CONTRACT_EXECUTOR_UNAVAILABLE",
            "CREDENTIALS_NOT_CONFIGURED",
            "CREDENTIALS_NOT_VERIFIED",
            "CREDENTIALS_TEST_DATE_MISSING",
            "CREDENTIALS_TEST_EXPIRED",
            "ITEM_ACTIVE_IN_PROCESS",
            "BROWSER_SESSION_BUSY",
            "ANOTHER_ITEM_PROCESSING",
            "EXECUTION_TERMINAL",
        }
    )

    def __init__(
        self,
        *,
        real_service: BatchContractExecutionService,
        dry_run_executor: ContractExecutor,
        evidence: ExecutionEvidenceRepository,
        real_write_enabled: bool,
        authorizations: RealWriteAuthorizationService,
        institutional_plans: InstitutionalTestPlanService | None = None,
    ) -> None:
        self._real = real_service
        self._dry_run = dry_run_executor
        self._evidence = evidence
        self._real_write_enabled = bool(real_write_enabled)
        self._authorizations = authorizations
        self._institutional_plans = institutional_plans
        self._simulation_lock = Lock()
        self._active_simulations: set[tuple[UUID, UUID]] = set()

    def preflight(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        actor_username: str = "",
        actor_user_id: int | None = None,
    ) -> BatchContractExecutionPreflight:
        selected_mode = ExecutionMode(mode)
        base = self._real.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        latest_evidence = self._evidence.get_latest(
            batch_id=batch_id,
            item_id=item_id,
            mode=selected_mode,
        )

        if selected_mode is ExecutionMode.REAL:
            authorization = (
                self._authorizations.get_latest(
                    batch_id=batch_id,
                    item_id=item_id,
                    actor_username=actor_username,
                    actor_user_id=actor_user_id,
                )
                if actor_username
                else None
            )
            institutional_plan = (
                self._institutional_plans.get_latest(
                    batch_id=batch_id,
                    item_id=item_id,
                    dependency=dependency,
                    actor_username=actor_username,
                    actor_user_id=actor_user_id,
                )
                if self._institutional_plans is not None
                and self._institutional_plans.enabled
                and actor_username
                else None
            )
            issues = list(base.issues)
            if self._real_write_enabled:
                authorization_issue = self._authorization_issue(
                    authorization
                )
                if authorization_issue is not None:
                    issues.append(authorization_issue)
                if (
                    self._institutional_plans is not None
                    and self._institutional_plans.enabled
                ):
                    plan_issue = (
                        self._institutional_plans.issue_for_preflight(
                            institutional_plan
                        )
                    )
                    if plan_issue is not None:
                        issues.append(
                            BatchContractExecutionIssue(
                                code=plan_issue[0],
                                message=plan_issue[1],
                            )
                        )

            return replace(
                base,
                issues=tuple(issues),
                mode=selected_mode,
                real_write_enabled=self._real_write_enabled,
                simulation_available=True,
                latest_correlation_id=(
                    latest_evidence.correlation_id
                    if latest_evidence is not None
                    else None
                ),
                real_write_authorization_required=True,
                authorization_available=(
                    authorization is not None
                    and authorization.status
                    is RealWriteAuthorizationStatus.ACTIVE
                ),
                authorization_id=(
                    authorization.authorization_id
                    if authorization is not None
                    else None
                ),
                authorization_status=(
                    authorization.status
                    if authorization is not None
                    else None
                ),
                authorization_expires_at=(
                    authorization.expires_at
                    if authorization is not None
                    else None
                ),
                authorization_required_confirmation=(
                    self._authorizations.required_issue_confirmation(
                        base.item.contract.contract_number
                    )
                ),
                authorization_ttl_seconds=(
                    self._authorizations.ttl_seconds
                ),
                institutional_plan_required=(
                    self._institutional_plans is not None
                    and self._institutional_plans.enabled
                ),
                institutional_plan_id=(
                    institutional_plan.plan_id
                    if institutional_plan is not None
                    else None
                ),
                institutional_plan_status=(
                    institutional_plan.status
                    if institutional_plan is not None
                    else None
                ),
                institutional_plan_expires_at=(
                    institutional_plan.expires_at
                    if institutional_plan is not None
                    else None
                ),
                institutional_plan_diagnostic_checked_at=(
                    institutional_plan.diagnostic_checked_at
                    if institutional_plan is not None
                    else None
                ),
                institutional_plan_ready=(
                    institutional_plan is not None
                    and institutional_plan.status
                    is InstitutionalTestPlanStatus.ARMED
                ),
                institutional_plan_required_confirmation=(
                    self._institutional_plans
                    .required_create_confirmation(
                        base.item.contract.contract_number
                    )
                    if self._institutional_plans is not None
                    and self._institutional_plans.enabled
                    else None
                ),
                institutional_plan_window_seconds=(
                    self._institutional_plans.window_seconds
                    if self._institutional_plans is not None
                    and self._institutional_plans.enabled
                    else None
                ),
            )

        issues: list[BatchContractExecutionIssue] = []
        for issue in base.issues:
            if issue.code in self.DRY_RUN_IGNORED_ISSUES:
                continue
            if issue.code == "TEST_VALUES_DETECTED":
                issues.append(
                    BatchContractExecutionIssue(
                        code=issue.code,
                        message=(
                            "Se detectaron valores unitarios de prueba. "
                            "La simulación puede continuar porque no escribe "
                            "en Gestión Transparente."
                        ),
                        blocking=False,
                    )
                )
                continue
            issues.append(issue)

        key = (batch_id, item_id)
        with self._simulation_lock:
            simulation_active = key in self._active_simulations
        if simulation_active:
            issues.append(
                BatchContractExecutionIssue(
                    code="DRY_RUN_IN_PROGRESS",
                    message="Este contrato ya tiene una simulación activa.",
                )
            )

        return replace(
            base,
            required_confirmation=self.required_confirmation(
                base.item.contract.contract_number,
                selected_mode,
            ),
            execution_enabled=True,
            executor_available=True,
            active_in_process=simulation_active,
            execution=None,
            resumable=False,
            issues=tuple(issues),
            mode=selected_mode,
            real_write_enabled=self._real_write_enabled,
            simulation_available=True,
            latest_correlation_id=(
                latest_evidence.correlation_id
                if latest_evidence is not None
                else None
            ),
            real_write_authorization_required=False,
            authorization_available=False,
            authorization_id=None,
            authorization_status=None,
            authorization_expires_at=None,
            authorization_required_confirmation=None,
            authorization_ttl_seconds=None,
        )

    def issue_real_write_authorization(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        actor_username: str,
        actor_user_id: int | None,
    ) -> IssuedRealWriteAuthorization:
        base = self._real.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        blocking = tuple(
            (issue.code, issue.message)
            for issue in base.issues
            if issue.blocking
        )
        if blocking:
            raise BatchContractExecutionBlockedError(blocking)

        return self._authorizations.issue(
            batch_id=batch_id,
            item_id=item_id,
            contract_number=base.item.contract.contract_number,
            dependency=base.batch.dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            confirmation=confirmation,
        )

    def get_real_write_authorization(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
    ) -> tuple[
        RealWriteAuthorization | None,
        tuple[RealWriteAuthorizationEvent, ...],
    ]:
        base = self._real.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        authorization = self._authorizations.get_latest(
            batch_id=batch_id,
            item_id=item_id,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
        )
        events = self._authorizations.list_events(
            batch_id=batch_id,
            item_id=item_id,
            authorization_id=None,
        )
        _ = base
        return authorization, events

    def revoke_real_write_authorization(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        actor_username: str,
        actor_user_id: int | None,
    ) -> tuple[
        RealWriteAuthorization,
        tuple[RealWriteAuthorizationEvent, ...],
    ]:
        base = self._real.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        authorization = self._authorizations.revoke(
            batch_id=batch_id,
            item_id=item_id,
            contract_number=base.item.contract.contract_number,
            dependency=base.batch.dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            confirmation=confirmation,
        )
        events = self._authorizations.list_events(
            batch_id=batch_id,
            item_id=item_id,
            authorization_id=None,
        )
        return authorization, events

    def execute(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        actor_username: str,
        actor_user_id: int | None,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        execution_id: UUID | None = None,
        authorization_token: str | None = None,
        institutional_plan_id: UUID | None = None,
    ) -> BatchContractExecutionResult:
        selected_mode = ExecutionMode(mode)
        preflight = self.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
            mode=selected_mode,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
        )
        blocking = tuple(
            (issue.code, issue.message)
            for issue in preflight.issues
            if issue.blocking
            and issue.code not in self.AUTHORIZATION_ISSUE_CODES
        )
        if blocking:
            raise BatchContractExecutionBlockedError(blocking)

        required = preflight.required_confirmation
        if self._confirmation_identity(confirmation) != (
            self._confirmation_identity(required)
        ):
            raise BatchContractExecutionConfirmationError(required)

        correlation_id = uuid4()
        started_at = datetime.now(UTC)

        if selected_mode is ExecutionMode.DRY_RUN:
            return self._execute_dry_run(
                preflight=preflight,
                correlation_id=correlation_id,
                started_at=started_at,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
            )

        if (
            self._institutional_plans is not None
            and self._institutional_plans.enabled
        ):
            if (
                institutional_plan_id is None
                or institutional_plan_id
                != preflight.institutional_plan_id
            ):
                raise InstitutionalTestPlanNotFoundError()

        try:
            authorization = self._authorizations.consume(
                token=authorization_token,
                batch_id=batch_id,
                item_id=item_id,
                contract_number=preflight.item.contract.contract_number,
                dependency=preflight.batch.dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                correlation_id=correlation_id,
            )
        except RealWriteAuthorizationError as error:
            self._save_failure(
                preflight=preflight,
                correlation_id=correlation_id,
                started_at=started_at,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                error=error,
                event_outcome="AUTHORIZATION_REJECTED",
                event_metadata={
                    "authorization_code": error.code,
                    "writes_to_portal": False,
                },
            )
            raise

        institutional_plan = None
        if (
            self._institutional_plans is not None
            and self._institutional_plans.enabled
        ):
            try:
                institutional_plan = self._institutional_plans.consume(
                    plan_id=institutional_plan_id,
                    batch_id=batch_id,
                    item_id=item_id,
                    contract_number=(
                        preflight.item.contract.contract_number
                    ),
                    dependency=preflight.batch.dependency,
                    actor_username=actor_username,
                    actor_user_id=actor_user_id,
                    correlation_id=correlation_id,
                )
            except InstitutionalTestPlanError as error:
                self._save_failure(
                    preflight=preflight,
                    correlation_id=correlation_id,
                    started_at=started_at,
                    actor_username=actor_username,
                    actor_user_id=actor_user_id,
                    error=error,
                    authorization=authorization,
                    event_outcome="INSTITUTIONAL_PLAN_REJECTED",
                    event_metadata={
                        "institutional_plan_code": error.code,
                        "writes_to_portal": False,
                    },
                )
                raise

        try:
            result = self._real.execute(
                batch_id=batch_id,
                item_id=item_id,
                dependency=dependency,
                confirmation=confirmation,
                execution_id=execution_id,
            )
        except Exception as error:
            self._save_failure(
                preflight=preflight,
                correlation_id=correlation_id,
                started_at=started_at,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                error=error,
                authorization=authorization,
            )
            raise

        evidence = self._evidence_from_result(
            result=result,
            preflight=preflight,
            correlation_id=correlation_id,
            started_at=started_at,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            authorization=authorization,
        )
        self._evidence.save(evidence)
        return replace(
            result,
            mode=selected_mode,
            correlation_id=correlation_id,
            writes_to_portal=True,
            evidence_count=evidence.evidence_count,
            authorization_id=authorization.authorization_id,
            authorization_consumed_at=authorization.consumed_at,
            institutional_plan_id=(
                institutional_plan.plan_id
                if institutional_plan is not None
                else None
            ),
            institutional_plan_consumed_at=(
                institutional_plan.consumed_at
                if institutional_plan is not None
                else None
            ),
        )

    def status(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        actor_username: str = "",
        actor_user_id: int | None = None,
    ) -> BatchContractExecutionResult:
        selected_mode = ExecutionMode(mode)
        if selected_mode is ExecutionMode.REAL:
            result = self._real.status(
                batch_id=batch_id,
                item_id=item_id,
                dependency=dependency,
            )
            latest = self._evidence.get_latest(
                batch_id=batch_id,
                item_id=item_id,
                mode=selected_mode,
            )
            authorization = (
                self._authorizations.get_latest(
                    batch_id=batch_id,
                    item_id=item_id,
                    actor_username=actor_username,
                    actor_user_id=actor_user_id,
                )
                if actor_username
                else None
            )
            return replace(
                result,
                mode=selected_mode,
                correlation_id=(
                    latest.correlation_id if latest is not None else None
                ),
                writes_to_portal=True,
                evidence_count=(
                    latest.evidence_count if latest is not None else 0
                ),
                authorization_id=(
                    authorization.authorization_id
                    if authorization is not None
                    else None
                ),
                authorization_consumed_at=(
                    authorization.consumed_at
                    if authorization is not None
                    else None
                ),
            )

        preflight = self.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
            mode=selected_mode,
        )
        latest = self._evidence.get_latest(
            batch_id=batch_id,
            item_id=item_id,
            mode=selected_mode,
        )
        if latest is None:
            return BatchContractExecutionResult(
                batch=preflight.batch,
                item=preflight.item,
                required_confirmation=preflight.required_confirmation,
                active_in_process=preflight.active_in_process,
                execution=None,
                transition_count=0,
                success=False,
                resumable=False,
                retry_pending=False,
                requires_manual_review=False,
                operational_message=(
                    "El contrato todavía no tiene una simulación registrada."
                ),
                mode=selected_mode,
                correlation_id=None,
                writes_to_portal=False,
                evidence_count=0,
            )

        execution = self._execution_from_evidence(latest)
        return BatchContractExecutionResult(
            batch=preflight.batch,
            item=preflight.item,
            required_confirmation=preflight.required_confirmation,
            active_in_process=preflight.active_in_process,
            execution=execution,
            transition_count=latest.evidence_count,
            success=latest.success,
            resumable=False,
            retry_pending=False,
            requires_manual_review=False,
            operational_message=latest.operational_message,
            error_code=latest.error_code,
            technical_detail=latest.technical_detail,
            mode=selected_mode,
            correlation_id=latest.correlation_id,
            writes_to_portal=False,
            evidence_count=latest.evidence_count,
        )

    def get_evidence(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        correlation_id: UUID,
        dependency: str,
    ) -> ContractExecutionEvidence:
        evidence = self._evidence.get(correlation_id)
        if evidence is None:
            raise ExecutionEvidenceNotFoundError(correlation_id)
        if (
            evidence.batch_id != batch_id
            or evidence.item_id != item_id
            or self._dependency_identity(evidence.dependency)
            != self._dependency_identity(dependency)
        ):
            raise ExecutionEvidenceContextError(
                "La evidencia no pertenece al contrato solicitado."
            )
        return evidence

    def list_evidence(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> tuple[ContractExecutionEvidence, ...]:
        preflight = self.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
            mode=ExecutionMode.DRY_RUN,
        )
        _ = preflight
        return self._evidence.list_for_item(
            batch_id=batch_id,
            item_id=item_id,
        )

    def _execute_dry_run(
        self,
        *,
        preflight: BatchContractExecutionPreflight,
        correlation_id: UUID,
        started_at: datetime,
        actor_username: str,
        actor_user_id: int | None,
    ) -> BatchContractExecutionResult:
        key = (preflight.batch.batch_id, preflight.item.item_id)
        with self._simulation_lock:
            if self._active_simulations:
                active_batch, active_item = next(iter(self._active_simulations))
                raise BatchContractExecutionInProgressError(
                    batch_id=active_batch,
                    item_id=active_item,
                )
            self._active_simulations.add(key)

        try:
            processing = self._dry_run.execute(
                contract=preflight.item.contract,
                execution_id=correlation_id,
            )
            result = BatchContractExecutionResult(
                batch=preflight.batch,
                item=preflight.item,
                required_confirmation=preflight.required_confirmation,
                active_in_process=False,
                execution=processing.execution,
                transition_count=len(processing.transitions),
                success=True,
                resumable=False,
                retry_pending=False,
                requires_manual_review=False,
                operational_message=(
                    "Simulación completada. No se abrió Chrome ni se "
                    "escribieron datos en Gestión Transparente."
                ),
                mode=ExecutionMode.DRY_RUN,
                correlation_id=correlation_id,
                writes_to_portal=False,
                transitions=processing.transitions,
            )
            evidence = self._evidence_from_result(
                result=result,
                preflight=preflight,
                correlation_id=correlation_id,
                started_at=started_at,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
            )
            self._evidence.save(evidence)
            return replace(result, evidence_count=evidence.evidence_count)
        except Exception as error:
            self._save_failure(
                preflight=preflight,
                correlation_id=correlation_id,
                started_at=started_at,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                error=error,
            )
            raise
        finally:
            with self._simulation_lock:
                self._active_simulations.discard(key)

    def _evidence_from_result(
        self,
        *,
        result: BatchContractExecutionResult,
        preflight: BatchContractExecutionPreflight,
        correlation_id: UUID,
        started_at: datetime,
        actor_username: str,
        actor_user_id: int | None,
        authorization: RealWriteAuthorization | None = None,
    ) -> ContractExecutionEvidence:
        events: list[ExecutionEvidenceEvent] = []
        if authorization is not None:
            events.append(
                ExecutionEvidenceEvent(
                    sequence=1,
                    step=None,
                    outcome="AUTHORIZATION_CONSUMED",
                    message=(
                        "Autorización temporal consumida antes de abrir "
                        "la sesión de escritura real."
                    ),
                    recorded_at=(
                        authorization.consumed_at
                        or datetime.now(UTC)
                    ),
                    metadata={
                        "authorization_id": str(
                            authorization.authorization_id
                        ),
                        "expires_at": authorization.expires_at.isoformat(),
                        "single_use": True,
                    },
                )
            )

        for transition in result.transitions:
            events.append(
                ExecutionEvidenceEvent(
                    sequence=len(events) + 1,
                    step=transition.step,
                    outcome=transition.outcome.value,
                    message=transition.message,
                    recorded_at=transition.execution.updated_at,
                    metadata={
                        "execution_status": transition.execution.status.value,
                        "mode": result.mode.value,
                    },
                )
            )

        if not result.transitions:
            events.append(
                ExecutionEvidenceEvent(
                    sequence=len(events) + 1,
                    step=result.last_completed_step,
                    outcome=(
                        "COMPLETED" if result.success else "STOPPED"
                    ),
                    message=result.operational_message,
                    recorded_at=datetime.now(UTC),
                    metadata={
                        "execution_status": (
                            result.execution_status.value
                            if result.execution_status is not None
                            else None
                        ),
                        "transition_count": result.transition_count,
                        "mode": result.mode.value,
                    },
                )
            )

        return ContractExecutionEvidence(
            correlation_id=correlation_id,
            mode=result.mode,
            batch_id=preflight.batch.batch_id,
            item_id=preflight.item.item_id,
            contract_number=preflight.item.contract.contract_number,
            dependency=preflight.batch.dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            status=(
                result.execution_status.value
                if result.execution_status is not None
                else ("COMPLETED" if result.success else "STOPPED")
            ),
            success=result.success,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            required_confirmation=preflight.required_confirmation,
            operational_message=result.operational_message,
            execution_id=result.execution_id,
            execution_status=result.execution_status,
            last_completed_step=result.last_completed_step,
            current_step=result.current_step,
            last_failed_step=result.last_failed_step,
            attempt_count=result.attempt_count,
            error_code=result.error_code,
            technical_detail=result.technical_detail,
            events=tuple(events),
        )

    def _save_failure(
        self,
        *,
        preflight: BatchContractExecutionPreflight,
        correlation_id: UUID,
        started_at: datetime,
        actor_username: str,
        actor_user_id: int | None,
        error: Exception,
        authorization: RealWriteAuthorization | None = None,
        event_outcome: str = "FAILED",
        event_metadata: dict[str, object] | None = None,
    ) -> None:
        completed_at = datetime.now(UTC)
        events: list[ExecutionEvidenceEvent] = []
        if authorization is not None:
            events.append(
                ExecutionEvidenceEvent(
                    sequence=1,
                    step=None,
                    outcome="AUTHORIZATION_CONSUMED",
                    message=(
                        "La autorización temporal fue consumida antes "
                        "del intento de escritura."
                    ),
                    recorded_at=(
                        authorization.consumed_at or completed_at
                    ),
                    metadata={
                        "authorization_id": str(
                            authorization.authorization_id
                        ),
                        "single_use": True,
                    },
                )
            )
        metadata = {
            "exception_type": type(error).__name__,
            "mode": preflight.mode.value,
        }
        metadata.update(event_metadata or {})
        events.append(
            ExecutionEvidenceEvent(
                sequence=len(events) + 1,
                step=None,
                outcome=event_outcome,
                message=str(error),
                recorded_at=completed_at,
                metadata=metadata,
            )
        )
        record = ContractExecutionEvidence(
            correlation_id=correlation_id,
            mode=preflight.mode,
            batch_id=preflight.batch.batch_id,
            item_id=preflight.item.item_id,
            contract_number=preflight.item.contract.contract_number,
            dependency=preflight.batch.dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            status="FAILED",
            success=False,
            started_at=started_at,
            completed_at=completed_at,
            required_confirmation=preflight.required_confirmation,
            operational_message=(
                "La ejecución controlada se detuvo antes de completarse."
            ),
            error_code=str(
                getattr(error, "code", type(error).__name__)
            ),
            technical_detail=f"{type(error).__name__}: {error}",
            events=tuple(events),
        )
        self._evidence.save(record)

    @staticmethod
    def _execution_from_evidence(
        evidence: ContractExecutionEvidence,
    ) -> ContractExecution:
        return ContractExecution(
            execution_id=evidence.execution_id or evidence.correlation_id,
            contract_number=evidence.contract_number,
            dependency=evidence.dependency,
            status=evidence.execution_status or (
                ExecutionStatus.COMPLETED
                if evidence.success
                else ExecutionStatus.FAILED
            ),
            last_completed_step=(
                evidence.last_completed_step or ContractStep.PENDING
            ),
            current_step=evidence.current_step,
            last_failed_step=evidence.last_failed_step,
            attempt_count=evidence.attempt_count,
            portal_profile=evidence.mode.value,
            last_error=None,
            created_at=evidence.started_at,
            started_at=evidence.started_at,
            updated_at=evidence.completed_at,
            completed_at=evidence.completed_at,
        )

    @staticmethod
    def required_confirmation(
        contract_number: str,
        mode: ExecutionMode,
    ) -> str:
        prefix = (
            "SIMULAR CONTRATO"
            if mode is ExecutionMode.DRY_RUN
            else "EJECUTAR CONTRATO"
        )
        return f"{prefix} {str(contract_number).strip()}"

    @staticmethod
    def _authorization_issue(
        authorization: RealWriteAuthorization | None,
    ) -> BatchContractExecutionIssue | None:
        if authorization is None:
            return BatchContractExecutionIssue(
                code="REAL_WRITE_AUTHORIZATION_REQUIRED",
                message=(
                    "Debe emitir una autorización temporal de un solo "
                    "uso para este contrato."
                ),
            )
        if authorization.status is RealWriteAuthorizationStatus.ACTIVE:
            return None
        messages = {
            RealWriteAuthorizationStatus.EXPIRED: (
                "La última autorización temporal venció."
            ),
            RealWriteAuthorizationStatus.CONSUMED: (
                "La última autorización temporal ya fue consumida."
            ),
            RealWriteAuthorizationStatus.REVOKED: (
                "La última autorización temporal fue revocada."
            ),
        }
        codes = {
            RealWriteAuthorizationStatus.EXPIRED: (
                "REAL_WRITE_AUTHORIZATION_EXPIRED"
            ),
            RealWriteAuthorizationStatus.CONSUMED: (
                "REAL_WRITE_AUTHORIZATION_ALREADY_CONSUMED"
            ),
            RealWriteAuthorizationStatus.REVOKED: (
                "REAL_WRITE_AUTHORIZATION_REVOKED"
            ),
        }
        return BatchContractExecutionIssue(
            code=codes[authorization.status],
            message=messages[authorization.status],
        )

    @staticmethod
    def _confirmation_identity(value: object) -> str:
        return " ".join(str(value).split()).casefold()

    @staticmethod
    def _dependency_identity(value: object) -> str:
        return " ".join(str(value).split()).casefold()
