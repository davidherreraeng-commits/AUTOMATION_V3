from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import UUID

from domain.enums import ContractStep, ExecutionMode, ExecutionStatus


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class ExecutionEvidenceEvent:
    sequence: int
    outcome: str
    recorded_at: datetime
    step: ContractStep | None = None
    message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("La secuencia de evidencia debe ser positiva.")
        outcome = str(self.outcome).strip().upper()
        if not outcome:
            raise ValueError("El resultado de la evidencia es obligatorio.")
        message = None if self.message is None else str(self.message).strip() or None
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at))
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "step": self.step.value if self.step is not None else None,
            "outcome": self.outcome,
            "message": self.message,
            "recorded_at": self.recorded_at.isoformat(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExecutionEvidenceEvent":
        step = payload.get("step")
        return cls(
            sequence=int(payload["sequence"]),
            step=ContractStep(step) if step else None,
            outcome=str(payload["outcome"]),
            message=payload.get("message"),
            recorded_at=datetime.fromisoformat(str(payload["recorded_at"])),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class ContractExecutionEvidence:
    correlation_id: UUID
    mode: ExecutionMode
    batch_id: UUID
    item_id: UUID
    contract_number: str
    dependency: str
    actor_username: str
    actor_user_id: int | None
    status: str
    success: bool
    started_at: datetime
    completed_at: datetime
    required_confirmation: str
    operational_message: str
    execution_id: UUID | None = None
    execution_status: ExecutionStatus | None = None
    last_completed_step: ContractStep | None = None
    current_step: ContractStep | None = None
    last_failed_step: ContractStep | None = None
    attempt_count: int = 0
    error_code: str | None = None
    technical_detail: str | None = None
    events: tuple[ExecutionEvidenceEvent, ...] = ()

    def __post_init__(self) -> None:
        contract_number = str(self.contract_number).strip()
        dependency = " ".join(str(self.dependency).split())
        actor_username = str(self.actor_username).strip()
        status = str(self.status).strip().upper()
        required_confirmation = " ".join(str(self.required_confirmation).split())
        operational_message = str(self.operational_message).strip()
        if not contract_number:
            raise ValueError("El número contractual de la evidencia es obligatorio.")
        if not dependency:
            raise ValueError("La dependencia de la evidencia es obligatoria.")
        if not actor_username:
            raise ValueError("El usuario auditor de la evidencia es obligatorio.")
        if not status:
            raise ValueError("El estado de la evidencia es obligatorio.")
        if not required_confirmation:
            raise ValueError("La confirmación auditada es obligatoria.")
        if not operational_message:
            raise ValueError("El mensaje operativo de la evidencia es obligatorio.")
        if self.attempt_count < 0:
            raise ValueError("Los intentos de la evidencia no pueden ser negativos.")
        object.__setattr__(self, "contract_number", contract_number)
        object.__setattr__(self, "dependency", dependency)
        object.__setattr__(self, "actor_username", actor_username)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "required_confirmation", required_confirmation)
        object.__setattr__(self, "operational_message", operational_message)
        object.__setattr__(self, "started_at", _utc(self.started_at))
        object.__setattr__(self, "completed_at", _utc(self.completed_at))
        object.__setattr__(self, "success", bool(self.success))
        object.__setattr__(self, "events", tuple(self.events))

    @property
    def evidence_count(self) -> int:
        return len(self.events)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": str(self.correlation_id),
            "mode": self.mode.value,
            "batch_id": str(self.batch_id),
            "item_id": str(self.item_id),
            "contract_number": self.contract_number,
            "dependency": self.dependency,
            "actor_username": self.actor_username,
            "actor_user_id": self.actor_user_id,
            "status": self.status,
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "required_confirmation": self.required_confirmation,
            "operational_message": self.operational_message,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "execution_status": (
                self.execution_status.value if self.execution_status else None
            ),
            "last_completed_step": (
                self.last_completed_step.value if self.last_completed_step else None
            ),
            "current_step": self.current_step.value if self.current_step else None,
            "last_failed_step": (
                self.last_failed_step.value if self.last_failed_step else None
            ),
            "attempt_count": self.attempt_count,
            "error_code": self.error_code,
            "technical_detail": self.technical_detail,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ContractExecutionEvidence":
        execution_status = payload.get("execution_status")
        last_completed = payload.get("last_completed_step")
        current = payload.get("current_step")
        last_failed = payload.get("last_failed_step")
        execution_id = payload.get("execution_id")
        return cls(
            correlation_id=UUID(str(payload["correlation_id"])),
            mode=ExecutionMode(str(payload["mode"])),
            batch_id=UUID(str(payload["batch_id"])),
            item_id=UUID(str(payload["item_id"])),
            contract_number=str(payload["contract_number"]),
            dependency=str(payload["dependency"]),
            actor_username=str(payload["actor_username"]),
            actor_user_id=payload.get("actor_user_id"),
            status=str(payload["status"]),
            success=bool(payload["success"]),
            started_at=datetime.fromisoformat(str(payload["started_at"])),
            completed_at=datetime.fromisoformat(str(payload["completed_at"])),
            required_confirmation=str(payload["required_confirmation"]),
            operational_message=str(payload["operational_message"]),
            execution_id=UUID(str(execution_id)) if execution_id else None,
            execution_status=(
                ExecutionStatus(str(execution_status)) if execution_status else None
            ),
            last_completed_step=(
                ContractStep(str(last_completed)) if last_completed else None
            ),
            current_step=ContractStep(str(current)) if current else None,
            last_failed_step=(
                ContractStep(str(last_failed)) if last_failed else None
            ),
            attempt_count=int(payload.get("attempt_count") or 0),
            error_code=payload.get("error_code"),
            technical_detail=payload.get("technical_detail"),
            events=tuple(
                ExecutionEvidenceEvent.from_dict(item)
                for item in payload.get("events") or ()
            ),
        )
