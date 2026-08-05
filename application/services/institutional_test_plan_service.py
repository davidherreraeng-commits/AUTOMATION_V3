from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from application.dto.institutional_test_plan import (
    InstitutionalTestPlan,
    InstitutionalTestPlanEvent,
)
from application.ports.institutional_test_plan_repository import (
    InstitutionalTestPlanRepository,
)
from application.services.batch_contract_execution_service import (
    BatchContractExecutionService,
)
from application.services.batch_portal_probe_service import (
    BatchPortalProbeService,
)
from domain.enums.institutional_test_plan_status import (
    InstitutionalTestPlanStatus,
)
from domain.errors.batch_contract_execution_errors import (
    BatchContractExecutionBlockedError,
)
from domain.errors.institutional_test_plan_errors import (
    InstitutionalTestPlanArmingDisabledError,
    InstitutionalTestPlanConfirmationError,
    InstitutionalTestPlanDiagnosticExpiredError,
    InstitutionalTestPlanDiagnosticRequiredError,
    InstitutionalTestPlanDisabledError,
    InstitutionalTestPlanNotArmedError,
    InstitutionalTestPlanNotFoundError,
)


class InstitutionalTestPlanService:
    """Administra una ventana supervisada para un único contrato."""

    PREPARATION_IGNORED_ISSUES = frozenset(
        {
            "EXECUTION_DISABLED",
            "CONTRACT_EXECUTOR_UNAVAILABLE",
            "ITEM_ACTIVE_IN_PROCESS",
            "BROWSER_SESSION_BUSY",
            "ANOTHER_ITEM_PROCESSING",
            "EXECUTION_TERMINAL",
        }
    )
    READ_ONLY_IGNORED_ISSUES = PREPARATION_IGNORED_ISSUES | frozenset(
        {
            "CREDENTIALS_NOT_VERIFIED",
            "CREDENTIALS_TEST_DATE_MISSING",
            "CREDENTIALS_TEST_EXPIRED",
            "TEST_VALUES_DETECTED",
        }
    )

    def __init__(
        self,
        *,
        repository: InstitutionalTestPlanRepository,
        executions: BatchContractExecutionService,
        portal_probe: BatchPortalProbeService,
        enabled: bool,
        arming_enabled: bool = False,
        window_seconds: int = 900,
        diagnostic_max_age_seconds: int = 300,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if window_seconds < 300 or window_seconds > 7200:
            raise ValueError(
                "La ventana institucional debe estar entre 300 y 7200 segundos."
            )
        if diagnostic_max_age_seconds < 60:
            raise ValueError(
                "La vigencia del diagnóstico debe ser de al menos 60 segundos."
            )
        if diagnostic_max_age_seconds > window_seconds:
            raise ValueError(
                "La vigencia del diagnóstico no puede superar la ventana."
            )
        self._repository = repository
        self._executions = executions
        self._portal_probe = portal_probe
        self._enabled = bool(enabled)
        self._arming_enabled = bool(arming_enabled)
        self._window_seconds = int(window_seconds)
        self._diagnostic_max_age_seconds = int(
            diagnostic_max_age_seconds
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def arming_enabled(self) -> bool:
        return self._arming_enabled

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    @property
    def diagnostic_max_age_seconds(self) -> int:
        return self._diagnostic_max_age_seconds

    def create(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        confirmation: str,
    ) -> InstitutionalTestPlan:
        self._ensure_enabled()
        base = self._prepare_contract(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
            ignored_issues=self.READ_ONLY_IGNORED_ISSUES,
        )
        contract_number = base.item.contract.contract_number
        required = self.required_create_confirmation(contract_number)
        self._assert_confirmation(confirmation, required)

        now = self._utc_now()
        return self._repository.create(
            InstitutionalTestPlan(
                plan_id=uuid4(),
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=base.batch.dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                status=InstitutionalTestPlanStatus.DRAFT,
                created_at=now,
                starts_at=now,
                expires_at=now
                + timedelta(seconds=self._window_seconds),
            )
        )

    def get_latest(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
    ) -> InstitutionalTestPlan | None:
        _ = dependency
        return self._repository.get_latest(
            batch_id=batch_id,
            item_id=item_id,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            now=self._utc_now(),
        )

    def status(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
    ) -> tuple[
        InstitutionalTestPlan | None,
        tuple[InstitutionalTestPlanEvent, ...],
        str,
        str,
    ]:
        base = self._load_contract_context(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        plan = self._repository.get_latest(
            batch_id=batch_id,
            item_id=item_id,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            now=self._utc_now(),
        )
        events = self._repository.list_events(
            batch_id=batch_id,
            item_id=item_id,
            plan_id=None,
        )
        return (
            plan,
            events,
            base.item.contract.contract_number,
            base.batch.dependency,
        )

    def run_read_only_diagnostic(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
    ) -> InstitutionalTestPlan:
        self._ensure_enabled()
        base = self._prepare_contract(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
            ignored_issues=self.READ_ONLY_IGNORED_ISSUES,
        )
        current = self._require_plan(
            plan_id=plan_id,
            batch_id=batch_id,
            item_id=item_id,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
        )
        outcome = self._portal_probe.run(
            batch_id=batch_id,
            dependency=dependency,
        )
        success = bool(
            outcome.success
            and outcome.authenticated
            and outcome.contracting_menu_found
            and outcome.enter_contract_found
            and outcome.assistant_access_found
        )
        return self._repository.record_diagnostic(
            plan_id=current.plan_id,
            batch_id=batch_id,
            item_id=item_id,
            contract_number=base.item.contract.contract_number,
            dependency=base.batch.dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            checked_at=outcome.checked_at,
            success=success,
            code=outcome.code,
            message=outcome.message,
            authenticated=outcome.authenticated,
            contracting_menu_found=outcome.contracting_menu_found,
            enter_contract_found=outcome.enter_contract_found,
            assistant_access_found=outcome.assistant_access_found,
            duration_ms=outcome.duration_ms,
        )

    def arm(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        confirmation: str,
    ) -> InstitutionalTestPlan:
        self._ensure_enabled()
        base = self._load_contract_context(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        contract_number = base.item.contract.contract_number
        current = self._require_plan(
            plan_id=plan_id,
            batch_id=batch_id,
            item_id=item_id,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
        )
        now = self._utc_now()

        if not self._arming_enabled:
            error = InstitutionalTestPlanArmingDisabledError()
            self._record_arm_rejection(
                plan=current,
                now=now,
                reason="ARMING_DISABLED",
                error=error,
            )
            raise error

        required = self.required_arm_confirmation(contract_number)
        try:
            self._assert_confirmation(confirmation, required)
        except InstitutionalTestPlanConfirmationError as error:
            self._record_arm_rejection(
                plan=current,
                now=now,
                reason="CONFIRMATION_MISMATCH",
                error=error,
            )
            raise

        blocking = tuple(
            (issue.code, issue.message)
            for issue in base.issues
            if issue.blocking
            and issue.code not in self.PREPARATION_IGNORED_ISSUES
        )
        if blocking:
            error = BatchContractExecutionBlockedError(blocking)
            self._record_arm_rejection(
                plan=current,
                now=now,
                reason="CONTRACT_SECURITY_BLOCK",
                error=error,
            )
            raise error

        return self._repository.arm(
            plan_id=plan_id,
            batch_id=batch_id,
            item_id=item_id,
            contract_number=contract_number,
            dependency=base.batch.dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            now=now,
            diagnostic_not_before=now
            - timedelta(seconds=self._diagnostic_max_age_seconds),
        )

    def cancel(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        confirmation: str,
    ) -> InstitutionalTestPlan:
        base = self._load_contract_context(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        contract_number = base.item.contract.contract_number
        required = self.required_cancel_confirmation(contract_number)
        self._assert_confirmation(confirmation, required)
        return self._repository.cancel(
            plan_id=plan_id,
            batch_id=batch_id,
            item_id=item_id,
            contract_number=contract_number,
            dependency=base.batch.dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            now=self._utc_now(),
            reason="MANUAL_CANCELLATION",
        )

    def consume(
        self,
        *,
        plan_id: UUID | None,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        correlation_id: UUID,
    ) -> InstitutionalTestPlan:
        self._ensure_enabled()
        if plan_id is None:
            raise InstitutionalTestPlanNotFoundError()
        return self._repository.consume(
            plan_id=plan_id,
            batch_id=batch_id,
            item_id=item_id,
            contract_number=contract_number,
            dependency=dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            now=self._utc_now(),
        )

    def issue_for_preflight(
        self,
        plan: InstitutionalTestPlan | None,
    ) -> tuple[str, str] | None:
        if plan is None:
            return (
                "INSTITUTIONAL_TEST_PLAN_REQUIRED",
                "Se requiere un plan institucional para este contrato.",
            )
        if plan.status is InstitutionalTestPlanStatus.ARMED:
            return None
        if plan.status is InstitutionalTestPlanStatus.READY:
            return (
                "INSTITUTIONAL_TEST_PLAN_NOT_ARMED",
                "El diagnóstico fue exitoso, pero el plan aún no está armado.",
            )
        if plan.status is InstitutionalTestPlanStatus.DRAFT:
            return (
                "INSTITUTIONAL_TEST_PLAN_DIAGNOSTIC_REQUIRED",
                "El plan requiere un diagnóstico read-only exitoso.",
            )
        return (
            f"INSTITUTIONAL_TEST_PLAN_{plan.status.value}",
            f"El plan institucional está en estado {plan.status.value}.",
        )

    def list_events(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        plan_id: UUID | None = None,
    ) -> tuple[InstitutionalTestPlanEvent, ...]:
        return self._repository.list_events(
            batch_id=batch_id,
            item_id=item_id,
            plan_id=plan_id,
        )

    def cleanup_expired(self, *, limit: int = 500) -> int:
        return self._repository.expire_due(
            now=self._utc_now(),
            limit=limit,
        )

    def _record_arm_rejection(
        self,
        *,
        plan: InstitutionalTestPlan,
        now: datetime,
        reason: str,
        error: Exception,
    ) -> None:
        self._repository.record_rejection(
            plan_id=plan.plan_id,
            batch_id=plan.batch_id,
            item_id=plan.item_id,
            contract_number=plan.contract_number,
            dependency=plan.dependency,
            actor_username=plan.actor_username,
            actor_user_id=plan.actor_user_id,
            now=now,
            reason=reason,
            code=getattr(error, "code", type(error).__name__),
            message=str(error),
        )

    def _require_plan(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        actor_username: str,
        actor_user_id: int | None,
    ) -> InstitutionalTestPlan:
        plan = self._repository.get_latest(
            batch_id=batch_id,
            item_id=item_id,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            now=self._utc_now(),
        )
        if plan is None or plan.plan_id != plan_id:
            raise InstitutionalTestPlanNotFoundError()
        return plan

    def _prepare_contract(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        ignored_issues: frozenset[str] | None = None,
    ):
        base = self._load_contract_context(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )
        ignored = (
            self.PREPARATION_IGNORED_ISSUES
            if ignored_issues is None
            else ignored_issues
        )
        blocking = tuple(
            (issue.code, issue.message)
            for issue in base.issues
            if issue.blocking and issue.code not in ignored
        )
        if blocking:
            raise BatchContractExecutionBlockedError(blocking)
        return base

    def _load_contract_context(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ):
        return self._executions.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=dependency,
        )

    def _ensure_enabled(self) -> None:
        if not self._enabled:
            raise InstitutionalTestPlanDisabledError()

    @staticmethod
    def required_create_confirmation(contract_number: str) -> str:
        return f"CREAR PLAN INSTITUCIONAL {str(contract_number).strip()}"

    @staticmethod
    def required_arm_confirmation(contract_number: str) -> str:
        return f"ARMAR PRUEBA INSTITUCIONAL {str(contract_number).strip()}"

    @staticmethod
    def required_cancel_confirmation(contract_number: str) -> str:
        return f"CANCELAR PLAN INSTITUCIONAL {str(contract_number).strip()}"

    @classmethod
    def _assert_confirmation(
        cls,
        value: str,
        required: str,
    ) -> None:
        if cls._identity(value) != cls._identity(required):
            raise InstitutionalTestPlanConfirmationError(required)

    def _utc_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _identity(value: object) -> str:
        return " ".join(str(value).split()).casefold()
