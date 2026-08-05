from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.real_write_authorization_repository import (
    SQLiteRealWriteAuthorizationRepository,
)
from application.dto.real_write_authorization import RealWriteAuthorization
from application.services.real_write_authorization_service import (
    RealWriteAuthorizationService,
)
from domain.enums import RealWriteAuthorizationStatus
from domain.errors.real_write_authorization_errors import (
    RealWriteAuthorizationConsumedError,
    RealWriteAuthorizationContextError,
    RealWriteAuthorizationExpiredError,
    RealWriteAuthorizationNotFoundError,
    RealWriteAuthorizationRevokedError,
)


BASE_TIME = datetime(2026, 8, 4, 18, 30, tzinfo=UTC)


def record(
    *,
    token_hash: str,
    batch_id=None,
    item_id=None,
    actor_username: str = "jefe",
    actor_user_id: int | None = 1,
    issued_at: datetime = BASE_TIME,
    expires_at: datetime | None = None,
) -> RealWriteAuthorization:
    return RealWriteAuthorization(
        authorization_id=uuid4(),
        token_hash=token_hash,
        batch_id=batch_id or uuid4(),
        item_id=item_id or uuid4(),
        contract_number="70-2026",
        dependency="Adquisiciones",
        actor_username=actor_username,
        actor_user_id=actor_user_id,
        status=RealWriteAuthorizationStatus.ACTIVE,
        issued_at=issued_at,
        expires_at=expires_at or issued_at + timedelta(minutes=5),
    )


def repository(tmp_path: Path) -> SQLiteRealWriteAuthorizationRepository:
    result = SQLiteRealWriteAuthorizationRepository(
        tmp_path / "authorizations.sqlite3"
    )
    result.initialize()
    return result


def test_should_consume_once_and_audit_replay(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    batch_id = uuid4()
    item_id = uuid4()
    raw_token = "token-temporal-seguro-1234567890"
    stored = repo.issue(
        record(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=item_id,
        )
    )
    correlation_id = uuid4()

    consumed = repo.consume(
        token_hash=RealWriteAuthorizationService.hash_token(raw_token),
        batch_id=batch_id,
        item_id=item_id,
        contract_number="70-2026",
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        correlation_id=correlation_id,
        now=BASE_TIME + timedelta(seconds=10),
    )

    assert consumed.status is RealWriteAuthorizationStatus.CONSUMED
    assert consumed.consumed_correlation_id == correlation_id
    assert consumed.consumed_at == BASE_TIME + timedelta(seconds=10)

    with pytest.raises(RealWriteAuthorizationConsumedError):
        repo.consume(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=item_id,
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            correlation_id=uuid4(),
            now=BASE_TIME + timedelta(seconds=20),
        )

    events = repo.list_events(
        batch_id=batch_id,
        item_id=item_id,
        authorization_id=stored.authorization_id,
    )
    assert [event.event_type for event in events] == [
        "ISSUED",
        "CONSUMED",
        "REJECTED",
    ]
    assert events[-1].reason == "ALREADY_CONSUMED"


def test_should_reject_foreign_context_without_consuming(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    batch_id = uuid4()
    item_id = uuid4()
    raw_token = "token-contexto-seguro-1234567890"
    stored = repo.issue(
        record(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=item_id,
        )
    )

    with pytest.raises(RealWriteAuthorizationContextError):
        repo.consume(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=uuid4(),
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            correlation_id=uuid4(),
            now=BASE_TIME + timedelta(seconds=5),
        )

    latest = repo.get_latest(
        batch_id=batch_id,
        item_id=item_id,
        actor_username="jefe",
        actor_user_id=1,
        now=BASE_TIME + timedelta(seconds=6),
    )
    assert latest is not None
    assert latest.authorization_id == stored.authorization_id
    assert latest.status is RealWriteAuthorizationStatus.ACTIVE


def test_should_expire_before_consumption(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    batch_id = uuid4()
    item_id = uuid4()
    raw_token = "token-expirable-seguro-1234567890"
    stored = repo.issue(
        record(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=item_id,
            expires_at=BASE_TIME + timedelta(seconds=60),
        )
    )

    with pytest.raises(RealWriteAuthorizationExpiredError):
        repo.consume(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=item_id,
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            correlation_id=uuid4(),
            now=BASE_TIME + timedelta(seconds=61),
        )

    latest = repo.get_latest(
        batch_id=batch_id,
        item_id=item_id,
        actor_username="jefe",
        actor_user_id=1,
        now=BASE_TIME + timedelta(seconds=62),
    )
    assert latest is not None
    assert latest.authorization_id == stored.authorization_id
    assert latest.status is RealWriteAuthorizationStatus.EXPIRED
    events = repo.list_events(
        batch_id=batch_id,
        item_id=item_id,
        authorization_id=stored.authorization_id,
    )
    assert [event.event_type for event in events] == [
        "ISSUED",
        "EXPIRED",
        "REJECTED",
    ]


def test_new_issue_should_revoke_previous_active_token(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    batch_id = uuid4()
    item_id = uuid4()
    first = repo.issue(
        record(
            token_hash="a" * 64,
            batch_id=batch_id,
            item_id=item_id,
        )
    )
    second = repo.issue(
        record(
            token_hash="b" * 64,
            batch_id=batch_id,
            item_id=item_id,
            issued_at=BASE_TIME + timedelta(seconds=10),
        )
    )

    first_events = repo.list_events(
        batch_id=batch_id,
        item_id=item_id,
        authorization_id=first.authorization_id,
    )
    latest = repo.get_latest(
        batch_id=batch_id,
        item_id=item_id,
        actor_username="jefe",
        actor_user_id=1,
        now=BASE_TIME + timedelta(seconds=11),
    )

    assert [event.event_type for event in first_events] == [
        "ISSUED",
        "REVOKED",
    ]
    assert latest is not None
    assert latest.authorization_id == second.authorization_id
    assert latest.status is RealWriteAuthorizationStatus.ACTIVE

def test_should_revoke_active_authorization_and_reject_token(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    batch_id = uuid4()
    item_id = uuid4()
    raw_token = "token-revocable-seguro-1234567890"
    stored = repo.issue(
        record(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=item_id,
        )
    )

    revoked = repo.revoke(
        batch_id=batch_id,
        item_id=item_id,
        contract_number="70-2026",
        dependency="Adquisiciones",
        actor_username="jefe",
        actor_user_id=1,
        now=BASE_TIME + timedelta(seconds=10),
    )

    assert revoked.authorization_id == stored.authorization_id
    assert revoked.status is RealWriteAuthorizationStatus.REVOKED
    assert revoked.revoked_at == BASE_TIME + timedelta(seconds=10)

    with pytest.raises(RealWriteAuthorizationRevokedError):
        repo.consume(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=item_id,
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            correlation_id=uuid4(),
            now=BASE_TIME + timedelta(seconds=11),
        )

    events = repo.list_events(
        batch_id=batch_id,
        item_id=item_id,
        authorization_id=stored.authorization_id,
    )
    assert [event.event_type for event in events] == [
        "ISSUED",
        "REVOKED",
        "REJECTED",
    ]
    assert events[1].reason == "MANUAL_REVOCATION"
    assert events[2].reason == "REVOKED"


def test_revoke_should_fail_when_authorization_does_not_exist(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    batch_id = uuid4()
    item_id = uuid4()

    with pytest.raises(RealWriteAuthorizationNotFoundError):
        repo.revoke(
            batch_id=batch_id,
            item_id=item_id,
            contract_number="70-2026",
            dependency="Adquisiciones",
            actor_username="jefe",
            actor_user_id=1,
            now=BASE_TIME,
        )

    events = repo.list_events(
        batch_id=batch_id,
        item_id=item_id,
    )
    assert len(events) == 1
    assert events[0].event_type == "REJECTED"
    assert events[0].reason == "REVOCATION_NOT_FOUND"


def test_should_sweep_all_due_active_authorizations(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    first_batch = uuid4()
    first_item = uuid4()
    second_batch = uuid4()
    second_item = uuid4()

    first = repo.issue(
        record(
            token_hash="c" * 64,
            batch_id=first_batch,
            item_id=first_item,
            expires_at=BASE_TIME + timedelta(seconds=30),
        )
    )
    second = repo.issue(
        record(
            token_hash="d" * 64,
            batch_id=second_batch,
            item_id=second_item,
            expires_at=BASE_TIME + timedelta(seconds=40),
        )
    )

    expired = repo.expire_due(
        now=BASE_TIME + timedelta(seconds=60),
    )
    repeated = repo.expire_due(
        now=BASE_TIME + timedelta(seconds=61),
    )

    assert expired == 2
    assert repeated == 0

    first_events = repo.list_events(
        batch_id=first_batch,
        item_id=first_item,
        authorization_id=first.authorization_id,
    )
    second_events = repo.list_events(
        batch_id=second_batch,
        item_id=second_item,
        authorization_id=second.authorization_id,
    )
    assert [event.event_type for event in first_events] == [
        "ISSUED",
        "EXPIRED",
    ]
    assert [event.event_type for event in second_events] == [
        "ISSUED",
        "EXPIRED",
    ]

@pytest.mark.parametrize(
    (
        "override",
        "expected_reason",
    ),
    [
        ({"batch_id": uuid4()}, "CONTEXT_MISMATCH"),
        ({"item_id": uuid4()}, "CONTEXT_MISMATCH"),
        ({"contract_number": "71-2026"}, "CONTEXT_MISMATCH"),
        ({"dependency": "Proyectos Especiales"}, "CONTEXT_MISMATCH"),
        ({"actor_username": "otro-jefe"}, "CONTEXT_MISMATCH"),
        ({"actor_user_id": 99}, "CONTEXT_MISMATCH"),
    ],
)
def test_token_should_be_bound_to_every_context_dimension(
    tmp_path: Path,
    override: dict[str, object],
    expected_reason: str,
) -> None:
    repo = repository(tmp_path)
    batch_id = uuid4()
    item_id = uuid4()
    raw_token = "token-contexto-completo-1234567890"
    stored = repo.issue(
        record(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            batch_id=batch_id,
            item_id=item_id,
        )
    )
    context = {
        "batch_id": batch_id,
        "item_id": item_id,
        "contract_number": "70-2026",
        "dependency": "Adquisiciones",
        "actor_username": "jefe",
        "actor_user_id": 1,
    }
    context.update(override)

    with pytest.raises(RealWriteAuthorizationContextError):
        repo.consume(
            token_hash=RealWriteAuthorizationService.hash_token(
                raw_token
            ),
            correlation_id=uuid4(),
            now=BASE_TIME + timedelta(seconds=5),
            **context,
        )

    latest = repo.get_latest(
        batch_id=batch_id,
        item_id=item_id,
        actor_username="jefe",
        actor_user_id=1,
        now=BASE_TIME + timedelta(seconds=6),
    )
    assert latest is not None
    assert latest.authorization_id == stored.authorization_id
    assert latest.status is RealWriteAuthorizationStatus.ACTIVE

    all_events = repo.list_events(
        batch_id=context["batch_id"],
        item_id=context["item_id"],
    )
    assert all_events[-1].event_type == "REJECTED"
    assert all_events[-1].reason == expected_reason

