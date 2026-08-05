from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from application.dto.real_write_authorization import (
    RealWriteAuthorization,
    RealWriteAuthorizationEvent,
)


class RealWriteAuthorizationRepository(Protocol):
    def initialize(self) -> None:
        ...

    def issue(
        self,
        authorization: RealWriteAuthorization,
    ) -> RealWriteAuthorization:
        ...

    def get_latest(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
    ) -> RealWriteAuthorization | None:
        ...

    def consume(
        self,
        *,
        token_hash: str,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        correlation_id: UUID,
        now: datetime,
    ) -> RealWriteAuthorization:
        ...

    def revoke(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
        reason: str = "MANUAL_REVOCATION",
    ) -> RealWriteAuthorization:
        ...

    def expire_due(
        self,
        *,
        now: datetime,
        limit: int = 500,
    ) -> int:
        ...

    def record_rejection(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        reason: str,
        recorded_at: datetime,
        correlation_id: UUID | None = None,
        authorization_id: UUID | None = None,
    ) -> None:
        ...

    def list_events(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        authorization_id: UUID | None = None,
    ) -> tuple[RealWriteAuthorizationEvent, ...]:
        ...
