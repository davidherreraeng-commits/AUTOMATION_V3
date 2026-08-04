from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from application.dto.real_write_authorization import (
    IssuedRealWriteAuthorization,
    RealWriteAuthorization,
    RealWriteAuthorizationEvent,
)
from application.ports.real_write_authorization_repository import (
    RealWriteAuthorizationRepository,
)
from domain.enums.real_write_authorization_status import (
    RealWriteAuthorizationStatus,
)
from domain.errors.real_write_authorization_errors import (
    RealWriteAuthorizationConfirmationError,
    RealWriteAuthorizationDisabledError,
    RealWriteAuthorizationRequiredError,
)


class RealWriteAuthorizationService:
    """Emite y consume autorizaciones opacas, temporales y de un solo uso."""

    def __init__(
        self,
        *,
        repository: RealWriteAuthorizationRepository,
        enabled: bool,
        ttl_seconds: int = 300,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if ttl_seconds < 60 or ttl_seconds > 1800:
            raise ValueError(
                "La vigencia de la autorización debe estar entre "
                "60 y 1800 segundos."
            )
        self._repository = repository
        self._enabled = bool(enabled)
        self._ttl_seconds = int(ttl_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def issue(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        confirmation: str,
    ) -> IssuedRealWriteAuthorization:
        self._ensure_enabled()
        required = self.required_issue_confirmation(contract_number)
        if self._identity(confirmation) != self._identity(required):
            raise RealWriteAuthorizationConfirmationError(required)

        issued_at = self._utc_now()
        token = secrets.token_urlsafe(32)
        authorization = RealWriteAuthorization(
            authorization_id=uuid4(),
            token_hash=self.hash_token(token),
            batch_id=batch_id,
            item_id=item_id,
            contract_number=contract_number,
            dependency=dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            status=RealWriteAuthorizationStatus.ACTIVE,
            issued_at=issued_at,
            expires_at=issued_at
            + timedelta(seconds=self._ttl_seconds),
        )
        stored = self._repository.issue(authorization)
        events = self._repository.list_events(
            batch_id=batch_id,
            item_id=item_id,
            authorization_id=stored.authorization_id,
        )
        return IssuedRealWriteAuthorization(
            authorization=stored,
            token=token,
            required_execution_confirmation=(
                self.required_execution_confirmation(contract_number)
            ),
            events=events,
        )

    def get_latest(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        actor_username: str,
        actor_user_id: int | None,
    ) -> RealWriteAuthorization | None:
        return self._repository.get_latest(
            batch_id=batch_id,
            item_id=item_id,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            now=self._utc_now(),
        )

    def consume(
        self,
        *,
        token: str | None,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        correlation_id: UUID,
    ) -> RealWriteAuthorization:
        self._ensure_enabled()
        normalized = str(token or "").strip()
        if not normalized:
            self._repository.record_rejection(
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                reason="MISSING_TOKEN",
                recorded_at=self._utc_now(),
                correlation_id=correlation_id,
            )
            raise RealWriteAuthorizationRequiredError()

        return self._repository.consume(
            token_hash=self.hash_token(normalized),
            batch_id=batch_id,
            item_id=item_id,
            contract_number=contract_number,
            dependency=dependency,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            now=self._utc_now(),
        )

    def list_events(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        authorization_id: UUID | None = None,
    ) -> tuple[RealWriteAuthorizationEvent, ...]:
        return self._repository.list_events(
            batch_id=batch_id,
            item_id=item_id,
            authorization_id=authorization_id,
        )

    def _ensure_enabled(self) -> None:
        if not self._enabled:
            raise RealWriteAuthorizationDisabledError()

    def _utc_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(
            str(token).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def required_issue_confirmation(contract_number: str) -> str:
        return (
            "AUTORIZAR ESCRITURA REAL "
            f"{str(contract_number).strip()}"
        )

    @staticmethod
    def required_execution_confirmation(contract_number: str) -> str:
        return f"EJECUTAR CONTRATO {str(contract_number).strip()}"

    @staticmethod
    def _identity(value: object) -> str:
        return " ".join(str(value).split()).casefold()
