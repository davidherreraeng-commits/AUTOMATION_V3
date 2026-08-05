from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from application.dto.institutional_test_plan import (
    InstitutionalTestPlan,
    InstitutionalTestPlanEvent,
)


class InstitutionalTestPlanRepository(Protocol):
    def initialize(self) -> None:
        ...

    def create(
        self,
        plan: InstitutionalTestPlan,
    ) -> InstitutionalTestPlan:
        ...

    def get_latest(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
    ) -> InstitutionalTestPlan | None:
        ...

    def record_diagnostic(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        checked_at: datetime,
        success: bool,
        code: str,
        message: str,
        authenticated: bool,
        contracting_menu_found: bool,
        enter_contract_found: bool,
        assistant_access_found: bool,
        duration_ms: int,
    ) -> InstitutionalTestPlan:
        ...

    def arm(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
        diagnostic_not_before: datetime,
    ) -> InstitutionalTestPlan:
        ...

    def record_rejection(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
        reason: str,
        code: str,
        message: str,
    ) -> InstitutionalTestPlan:
        ...

    def consume(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        correlation_id: UUID,
        now: datetime,
    ) -> InstitutionalTestPlan:
        ...

    def cancel(
        self,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
        reason: str,
    ) -> InstitutionalTestPlan:
        ...

    def expire_due(
        self,
        *,
        now: datetime,
        limit: int = 500,
    ) -> int:
        ...

    def list_events(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        plan_id: UUID | None = None,
    ) -> tuple[InstitutionalTestPlanEvent, ...]:
        ...
