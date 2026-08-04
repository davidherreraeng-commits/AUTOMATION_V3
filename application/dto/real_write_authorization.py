from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import UUID

from domain.enums.real_write_authorization_status import (
    RealWriteAuthorizationStatus,
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class RealWriteAuthorizationEvent:
    event_id: UUID
    event_type: str
    batch_id: UUID
    item_id: UUID
    contract_number: str
    dependency: str
    actor_username: str
    actor_user_id: int | None
    recorded_at: datetime
    authorization_id: UUID | None = None
    correlation_id: UUID | None = None
    reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        event_type = str(self.event_type).strip().upper()
        contract_number = str(self.contract_number).strip()
        dependency = " ".join(str(self.dependency).split())
        actor_username = str(self.actor_username).strip()
        reason = (
            None
            if self.reason is None
            else str(self.reason).strip() or None
        )
        if not event_type:
            raise ValueError("El tipo de evento de autorización es obligatorio.")
        if not contract_number:
            raise ValueError("El número contractual es obligatorio.")
        if not dependency:
            raise ValueError("La dependencia es obligatoria.")
        if not actor_username:
            raise ValueError("El usuario auditor es obligatorio.")
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "contract_number", contract_number)
        object.__setattr__(self, "dependency", dependency)
        object.__setattr__(self, "actor_username", actor_username)
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at))
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class RealWriteAuthorization:
    authorization_id: UUID
    token_hash: str
    batch_id: UUID
    item_id: UUID
    contract_number: str
    dependency: str
    actor_username: str
    actor_user_id: int | None
    status: RealWriteAuthorizationStatus
    issued_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
    consumed_correlation_id: UUID | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        token_hash = str(self.token_hash).strip().lower()
        contract_number = str(self.contract_number).strip()
        dependency = " ".join(str(self.dependency).split())
        actor_username = str(self.actor_username).strip()
        if len(token_hash) != 64 or any(
            character not in "0123456789abcdef"
            for character in token_hash
        ):
            raise ValueError("La huella de la autorización no es válida.")
        if not contract_number:
            raise ValueError("El número contractual es obligatorio.")
        if not dependency:
            raise ValueError("La dependencia es obligatoria.")
        if not actor_username:
            raise ValueError("El usuario autorizado es obligatorio.")
        issued_at = _utc(self.issued_at)
        expires_at = _utc(self.expires_at)
        if expires_at <= issued_at:
            raise ValueError(
                "La autorización debe vencer después de su emisión."
            )
        object.__setattr__(self, "token_hash", token_hash)
        object.__setattr__(self, "contract_number", contract_number)
        object.__setattr__(self, "dependency", dependency)
        object.__setattr__(self, "actor_username", actor_username)
        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(
            self,
            "consumed_at",
            _utc(self.consumed_at)
            if self.consumed_at is not None
            else None,
        )
        object.__setattr__(
            self,
            "revoked_at",
            _utc(self.revoked_at)
            if self.revoked_at is not None
            else None,
        )

    def is_active_at(self, now: datetime) -> bool:
        return (
            self.status is RealWriteAuthorizationStatus.ACTIVE
            and _utc(now) < self.expires_at
        )


@dataclass(frozen=True, slots=True)
class IssuedRealWriteAuthorization:
    authorization: RealWriteAuthorization
    token: str
    required_execution_confirmation: str
    events: tuple[RealWriteAuthorizationEvent, ...] = ()

    def __post_init__(self) -> None:
        token = str(self.token).strip()
        confirmation = " ".join(
            str(self.required_execution_confirmation).split()
        )
        if not token:
            raise ValueError("El token temporal es obligatorio.")
        if not confirmation:
            raise ValueError(
                "La confirmación de ejecución real es obligatoria."
            )
        object.__setattr__(self, "token", token)
        object.__setattr__(
            self,
            "required_execution_confirmation",
            confirmation,
        )
        object.__setattr__(self, "events", tuple(self.events))
