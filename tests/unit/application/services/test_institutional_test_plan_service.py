from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.institutional_test_plan_repository import (
    SQLiteInstitutionalTestPlanRepository,
)
from application.services.institutional_test_plan_service import (
    InstitutionalTestPlanService,
)
from domain.enums import InstitutionalTestPlanStatus
from domain.errors import (
    BatchContractExecutionBlockedError,
    InstitutionalTestPlanConfirmationError,
)


class FakeExecutionService:
    def __init__(self, issues=()) -> None:
        self.issues = tuple(issues)

    def preflight(self, *, batch_id, item_id, dependency):
        return SimpleNamespace(
            issues=self.issues,
            batch=SimpleNamespace(dependency=dependency),
            item=SimpleNamespace(
                contract=SimpleNamespace(contract_number="70-2026")
            ),
        )


class FakePortalProbeService:
    def __init__(self, *, success: bool = True) -> None:
        self.success = success
        self.calls = 0

    def run(self, *, batch_id, dependency):
        self.calls += 1
        return SimpleNamespace(
            success=self.success,
            code="PORTAL_READY" if self.success else "PORTAL_BLOCKED",
            message="Diagnóstico read-only.",
            authenticated=self.success,
            contracting_menu_found=self.success,
            enter_contract_found=self.success,
            assistant_access_found=self.success,
            duration_ms=800,
            checked_at=datetime.now(UTC),
        )


def test_should_create_diagnose_and_arm_plan(tmp_path) -> None:
    repository = SQLiteInstitutionalTestPlanRepository(
        tmp_path / "rpa.sqlite3"
    )
    repository.initialize()
    probe = FakePortalProbeService()
    service = InstitutionalTestPlanService(
        repository=repository,
        executions=FakeExecutionService(),
        portal_probe=probe,
        enabled=True,
        arming_enabled=True,
        window_seconds=900,
        diagnostic_max_age_seconds=300,
    )
    batch_id = uuid4()
    item_id = uuid4()

    with pytest.raises(InstitutionalTestPlanConfirmationError):
        service.create(
            batch_id=batch_id,
            item_id=item_id,
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            confirmation="CREAR PLAN INSTITUCIONAL 71-2026",
        )

    created = service.create(
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        confirmation="CREAR PLAN INSTITUCIONAL 70-2026",
    )
    assert created.status is InstitutionalTestPlanStatus.DRAFT

    ready = service.run_read_only_diagnostic(
        plan_id=created.plan_id,
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
    )
    assert ready.status is InstitutionalTestPlanStatus.READY
    assert ready.diagnostic_success is True
    assert probe.calls == 1

    armed = service.arm(
        plan_id=created.plan_id,
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        confirmation="ARMAR PRUEBA INSTITUCIONAL 70-2026",
    )
    assert armed.status is InstitutionalTestPlanStatus.ARMED
    assert service.issue_for_preflight(armed) is None


def test_failed_read_only_diagnostic_should_keep_plan_in_draft(tmp_path) -> None:
    repository = SQLiteInstitutionalTestPlanRepository(
        tmp_path / "rpa.sqlite3"
    )
    repository.initialize()
    service = InstitutionalTestPlanService(
        repository=repository,
        executions=FakeExecutionService(),
        portal_probe=FakePortalProbeService(success=False),
        enabled=True,
    )
    batch_id = uuid4()
    item_id = uuid4()
    created = service.create(
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        confirmation="CREAR PLAN INSTITUCIONAL 70-2026",
    )

    checked = service.run_read_only_diagnostic(
        plan_id=created.plan_id,
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
    )

    assert checked.status is InstitutionalTestPlanStatus.DRAFT
    assert checked.diagnostic_success is False
    issue = service.issue_for_preflight(checked)
    assert issue is not None
    assert issue[0] == "INSTITUTIONAL_TEST_PLAN_DIAGNOSTIC_REQUIRED"


def test_read_only_plan_should_ignore_real_write_only_blockers(tmp_path) -> None:
    repository = SQLiteInstitutionalTestPlanRepository(
        tmp_path / "rpa.sqlite3"
    )
    repository.initialize()
    issues = (
        SimpleNamespace(
            code="CREDENTIALS_TEST_EXPIRED",
            message="La prueba de credenciales expiró.",
            blocking=True,
        ),
        SimpleNamespace(
            code="TEST_VALUES_DETECTED",
            message="El contrato contiene valores de prueba.",
            blocking=True,
        ),
    )
    probe = FakePortalProbeService()
    service = InstitutionalTestPlanService(
        repository=repository,
        executions=FakeExecutionService(issues),
        portal_probe=probe,
        enabled=True,
        arming_enabled=True,
    )
    batch_id = uuid4()
    item_id = uuid4()

    plan, events, contract_number, dependency = service.status(
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
    )
    assert plan is None
    assert events == ()
    assert contract_number == "70-2026"
    assert dependency == "Adquisiciones"

    created = service.create(
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        confirmation="CREAR PLAN INSTITUCIONAL 70-2026",
    )
    assert created.status is InstitutionalTestPlanStatus.DRAFT

    checked = service.run_read_only_diagnostic(
        plan_id=created.plan_id,
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
    )
    assert checked.status is InstitutionalTestPlanStatus.READY
    assert probe.calls == 1

    with pytest.raises(BatchContractExecutionBlockedError) as captured:
        service.arm(
            plan_id=created.plan_id,
            batch_id=batch_id,
            item_id=item_id,
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            confirmation="ARMAR PRUEBA INSTITUCIONAL 70-2026",
        )
    assert "valores de prueba" in str(captured.value)

def test_arming_should_require_independent_server_flag_and_audit_rejection(
    tmp_path,
) -> None:
    repository = SQLiteInstitutionalTestPlanRepository(
        tmp_path / "rpa.sqlite3"
    )
    repository.initialize()
    service = InstitutionalTestPlanService(
        repository=repository,
        executions=FakeExecutionService(),
        portal_probe=FakePortalProbeService(),
        enabled=True,
        arming_enabled=False,
    )
    batch_id = uuid4()
    item_id = uuid4()
    created = service.create(
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        confirmation="CREAR PLAN INSTITUCIONAL 70-2026",
    )
    ready = service.run_read_only_diagnostic(
        plan_id=created.plan_id,
        batch_id=batch_id,
        item_id=item_id,
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
    )
    assert ready.status is InstitutionalTestPlanStatus.READY

    from domain.errors import InstitutionalTestPlanArmingDisabledError

    with pytest.raises(InstitutionalTestPlanArmingDisabledError):
        service.arm(
            plan_id=created.plan_id,
            batch_id=batch_id,
            item_id=item_id,
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            confirmation="ARMAR PRUEBA INSTITUCIONAL 70-2026",
        )

    events = service.list_events(
        batch_id=batch_id,
        item_id=item_id,
        plan_id=created.plan_id,
    )
    rejected = [event for event in events if event.event_type == "ARM_REJECTED"]
    assert len(rejected) == 1
    assert rejected[0].reason == "ARMING_DISABLED"
    assert rejected[0].metadata["writes_to_portal"] is False

