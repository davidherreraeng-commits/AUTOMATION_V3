from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.institutional_test_plan_repository import (
    SQLiteInstitutionalTestPlanRepository,
)
from application.dto.institutional_test_plan import InstitutionalTestPlan
from domain.enums import InstitutionalTestPlanStatus
from domain.errors import (
    InstitutionalTestPlanConsumedError,
    InstitutionalTestPlanContextError,
    InstitutionalTestPlanExpiredError,
)


def make_plan(now: datetime) -> InstitutionalTestPlan:
    return InstitutionalTestPlan(
        plan_id=uuid4(),
        batch_id=uuid4(),
        item_id=uuid4(),
        contract_number="70-2026",
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        status=InstitutionalTestPlanStatus.DRAFT,
        created_at=now,
        starts_at=now,
        expires_at=now + timedelta(minutes=15),
    )


def test_should_complete_single_use_plan_lifecycle(tmp_path) -> None:
    repository = SQLiteInstitutionalTestPlanRepository(
        tmp_path / "rpa.sqlite3"
    )
    repository.initialize()
    now = datetime.now(UTC)
    created = repository.create(make_plan(now))

    ready = repository.record_diagnostic(
        plan_id=created.plan_id,
        batch_id=created.batch_id,
        item_id=created.item_id,
        contract_number=created.contract_number,
        dependency=created.dependency,
        actor_username=created.actor_username,
        actor_user_id=created.actor_user_id,
        checked_at=now + timedelta(seconds=10),
        success=True,
        code="PORTAL_READY",
        message="Acceso read-only confirmado.",
        authenticated=True,
        contracting_menu_found=True,
        enter_contract_found=True,
        assistant_access_found=True,
        duration_ms=1250,
    )
    assert ready.status is InstitutionalTestPlanStatus.READY
    assert ready.diagnostic_success is True

    armed = repository.arm(
        plan_id=created.plan_id,
        batch_id=created.batch_id,
        item_id=created.item_id,
        contract_number=created.contract_number,
        dependency=created.dependency,
        actor_username=created.actor_username,
        actor_user_id=created.actor_user_id,
        now=now + timedelta(seconds=20),
        diagnostic_not_before=now,
    )
    assert armed.status is InstitutionalTestPlanStatus.ARMED

    correlation_id = uuid4()
    consumed = repository.consume(
        plan_id=created.plan_id,
        batch_id=created.batch_id,
        item_id=created.item_id,
        contract_number=created.contract_number,
        dependency=created.dependency,
        actor_username=created.actor_username,
        actor_user_id=created.actor_user_id,
        correlation_id=correlation_id,
        now=now + timedelta(seconds=30),
    )
    assert consumed.status is InstitutionalTestPlanStatus.CONSUMED
    assert consumed.execution_count == 1
    assert consumed.consumed_correlation_id == correlation_id

    with pytest.raises(InstitutionalTestPlanConsumedError):
        repository.consume(
            plan_id=created.plan_id,
            batch_id=created.batch_id,
            item_id=created.item_id,
            contract_number=created.contract_number,
            dependency=created.dependency,
            actor_username=created.actor_username,
            actor_user_id=created.actor_user_id,
            correlation_id=uuid4(),
            now=now + timedelta(seconds=31),
        )

    assert {
        event.event_type
        for event in repository.list_events(
            batch_id=created.batch_id,
            item_id=created.item_id,
        )
    } >= {"CREATED", "DIAGNOSTIC_PASSED", "ARMED", "CONSUMED"}


def test_should_reject_context_and_expire_window(tmp_path) -> None:
    repository = SQLiteInstitutionalTestPlanRepository(
        tmp_path / "rpa.sqlite3"
    )
    repository.initialize()
    now = datetime.now(UTC)
    plan = make_plan(now)
    expired_plan = InstitutionalTestPlan(
        plan_id=plan.plan_id,
        batch_id=plan.batch_id,
        item_id=plan.item_id,
        contract_number=plan.contract_number,
        dependency=plan.dependency,
        actor_username=plan.actor_username,
        actor_user_id=plan.actor_user_id,
        status=plan.status,
        created_at=plan.created_at,
        starts_at=plan.starts_at,
        expires_at=now + timedelta(seconds=1),
    )
    created = repository.create(expired_plan)

    with pytest.raises(InstitutionalTestPlanContextError):
        repository.cancel(
            plan_id=created.plan_id,
            batch_id=created.batch_id,
            item_id=created.item_id,
            contract_number=created.contract_number,
            dependency="Otra dependencia",
            actor_username=created.actor_username,
            actor_user_id=created.actor_user_id,
            now=now,
            reason="TEST",
        )

    with pytest.raises(InstitutionalTestPlanExpiredError):
        repository.arm(
            plan_id=created.plan_id,
            batch_id=created.batch_id,
            item_id=created.item_id,
            contract_number=created.contract_number,
            dependency=created.dependency,
            actor_username=created.actor_username,
            actor_user_id=created.actor_user_id,
            now=now + timedelta(seconds=2),
            diagnostic_not_before=now,
        )
