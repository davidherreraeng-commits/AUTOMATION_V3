from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.real_write_authorization_repository import (
    SQLiteRealWriteAuthorizationRepository,
)
from application.services.real_write_authorization_service import (
    RealWriteAuthorizationService,
)
from domain.enums import RealWriteAuthorizationStatus
from domain.errors.real_write_authorization_errors import (
    RealWriteAuthorizationConfirmationError,
    RealWriteAuthorizationDisabledError,
    RealWriteAuthorizationRequiredError,
)


class Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def service(
    tmp_path: Path,
    *,
    enabled: bool = True,
    clock: Clock | None = None,
) -> RealWriteAuthorizationService:
    repository = SQLiteRealWriteAuthorizationRepository(
        tmp_path / "authorization-service.sqlite3"
    )
    repository.initialize()
    return RealWriteAuthorizationService(
        repository=repository,
        enabled=enabled,
        ttl_seconds=120,
        clock=clock,
    )


def test_should_issue_opaque_token_bound_to_context(
    tmp_path: Path,
) -> None:
    clock = Clock(datetime(2026, 8, 4, 18, 45, tzinfo=UTC))
    authorizations = service(tmp_path, clock=clock)
    batch_id = uuid4()
    item_id = uuid4()

    issued = authorizations.issue(
        batch_id=batch_id,
        item_id=item_id,
        contract_number="70-2026",
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        confirmation="AUTORIZAR ESCRITURA REAL 70-2026",
    )

    assert issued.authorization.status is RealWriteAuthorizationStatus.ACTIVE
    assert issued.authorization.batch_id == batch_id
    assert issued.authorization.item_id == item_id
    assert issued.authorization.expires_at == (
        clock.value + timedelta(seconds=120)
    )
    assert issued.token not in issued.authorization.token_hash
    assert (
        RealWriteAuthorizationService.hash_token(issued.token)
        == issued.authorization.token_hash
    )
    assert issued.events[0].event_type == "ISSUED"


def test_should_require_exact_authorization_confirmation(
    tmp_path: Path,
) -> None:
    authorizations = service(tmp_path)

    with pytest.raises(RealWriteAuthorizationConfirmationError) as error:
        authorizations.issue(
            batch_id=uuid4(),
            item_id=uuid4(),
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            confirmation="EJECUTAR CONTRATO 70-2026",
        )

    assert (
        error.value.required_confirmation
        == "AUTORIZAR ESCRITURA REAL 70-2026"
    )


def test_should_keep_real_write_disabled_without_server_gate(
    tmp_path: Path,
) -> None:
    authorizations = service(tmp_path, enabled=False)

    with pytest.raises(RealWriteAuthorizationDisabledError):
        authorizations.issue(
            batch_id=uuid4(),
            item_id=uuid4(),
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            confirmation="AUTORIZAR ESCRITURA REAL 70-2026",
        )


def test_missing_token_should_be_audited_and_rejected(
    tmp_path: Path,
) -> None:
    authorizations = service(tmp_path)
    batch_id = uuid4()
    item_id = uuid4()
    correlation_id = uuid4()

    with pytest.raises(RealWriteAuthorizationRequiredError):
        authorizations.consume(
            token=None,
            batch_id=batch_id,
            item_id=item_id,
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            correlation_id=correlation_id,
        )

    events = authorizations.list_events(
        batch_id=batch_id,
        item_id=item_id,
    )
    assert len(events) == 1
    assert events[0].event_type == "REJECTED"
    assert events[0].reason == "MISSING_TOKEN"
    assert events[0].correlation_id == correlation_id
