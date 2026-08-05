from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import UUID

from domain.enums.institutional_test_plan_status import (
    InstitutionalTestPlanStatus,
)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class InstitutionalTestPlanEvent:
    event_id: UUID
    plan_id: UUID | None
    event_type: str
    batch_id: UUID
    item_id: UUID
    contract_number: str
    dependency: str
    actor_username: str
    actor_user_id: int | None
    recorded_at: datetime
    correlation_id: UUID | None = None
    reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "event_type",
            str(self.event_type).strip().upper(),
        )
        object.__setattr__(
            self,
            "contract_number",
            str(self.contract_number).strip(),
        )
        object.__setattr__(
            self,
            "dependency",
            " ".join(str(self.dependency).split()),
        )
        object.__setattr__(
            self,
            "actor_username",
            str(self.actor_username).strip(),
        )
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at))
        object.__setattr__(
            self,
            "reason",
            str(self.reason).strip() if self.reason else None,
        )
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class InstitutionalTestPlan:
    plan_id: UUID
    batch_id: UUID
    item_id: UUID
    contract_number: str
    dependency: str
    actor_username: str
    actor_user_id: int | None
    status: InstitutionalTestPlanStatus
    created_at: datetime
    starts_at: datetime
    expires_at: datetime
    max_executions: int = 1
    execution_count: int = 0
    diagnostic_checked_at: datetime | None = None
    diagnostic_success: bool | None = None
    diagnostic_code: str | None = None
    diagnostic_message: str | None = None
    diagnostic_authenticated: bool = False
    diagnostic_contracting_menu_found: bool = False
    diagnostic_enter_contract_found: bool = False
    diagnostic_assistant_access_found: bool = False
    diagnostic_duration_ms: int | None = None
    armed_at: datetime | None = None
    consumed_at: datetime | None = None
    consumed_correlation_id: UUID | None = None
    cancelled_at: datetime | None = None

    def __post_init__(self) -> None:
        created_at = _utc(self.created_at)
        starts_at = _utc(self.starts_at)
        expires_at = _utc(self.expires_at)
        if created_at is None or starts_at is None or expires_at is None:
            raise ValueError("Las fechas del plan son obligatorias.")
        if expires_at <= starts_at:
            raise ValueError("El plan debe vencer después de iniciar.")
        if self.max_executions != 1:
            raise ValueError("El plan institucional admite una sola ejecución.")
        if self.execution_count < 0 or self.execution_count > 1:
            raise ValueError("El contador de ejecución del plan no es válido.")
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "starts_at", starts_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(
            self,
            "diagnostic_checked_at",
            _utc(self.diagnostic_checked_at),
        )
        object.__setattr__(self, "armed_at", _utc(self.armed_at))
        object.__setattr__(self, "consumed_at", _utc(self.consumed_at))
        object.__setattr__(self, "cancelled_at", _utc(self.cancelled_at))
        object.__setattr__(
            self,
            "contract_number",
            str(self.contract_number).strip(),
        )
        object.__setattr__(
            self,
            "dependency",
            " ".join(str(self.dependency).split()),
        )
        object.__setattr__(
            self,
            "actor_username",
            str(self.actor_username).strip(),
        )

    def is_window_active_at(self, now: datetime) -> bool:
        normalized = _utc(now)
        assert normalized is not None
        return self.starts_at <= normalized < self.expires_at
