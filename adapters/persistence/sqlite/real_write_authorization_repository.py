from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from application.dto.real_write_authorization import (
    RealWriteAuthorization,
    RealWriteAuthorizationEvent,
)
from domain.enums.real_write_authorization_status import (
    RealWriteAuthorizationStatus,
)
from domain.errors.real_write_authorization_errors import (
    RealWriteAuthorizationConsumedError,
    RealWriteAuthorizationContextError,
    RealWriteAuthorizationExpiredError,
    RealWriteAuthorizationInvalidError,
    RealWriteAuthorizationNotFoundError,
    RealWriteAuthorizationRepositoryError,
    RealWriteAuthorizationRevokedError,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS real_write_authorizations (
    authorization_id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    batch_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    contract_number TEXT NOT NULL,
    contract_identity TEXT NOT NULL,
    dependency TEXT NOT NULL,
    dependency_identity TEXT NOT NULL,
    actor_username TEXT NOT NULL,
    actor_identity TEXT NOT NULL,
    actor_user_id INTEGER,
    status TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    consumed_correlation_id TEXT,
    revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS
    idx_real_write_authorizations_context
ON real_write_authorizations(
    batch_id,
    item_id,
    actor_identity,
    issued_at DESC
);

CREATE UNIQUE INDEX IF NOT EXISTS
    uq_active_real_write_authorization_per_item
ON real_write_authorizations(batch_id, item_id)
WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS real_write_authorization_events (
    event_id TEXT PRIMARY KEY,
    authorization_id TEXT,
    event_type TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    contract_number TEXT NOT NULL,
    dependency TEXT NOT NULL,
    actor_username TEXT NOT NULL,
    actor_user_id INTEGER,
    recorded_at TEXT NOT NULL,
    correlation_id TEXT,
    reason TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS
    idx_real_write_authorization_events_context
ON real_write_authorization_events(
    batch_id,
    item_id,
    recorded_at ASC
);

CREATE INDEX IF NOT EXISTS
    idx_real_write_authorization_events_authorization
ON real_write_authorization_events(
    authorization_id,
    recorded_at ASC
);
"""


def _identity(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_text(value: datetime | None) -> str | None:
    return _utc(value).isoformat() if value is not None else None


def _from_text(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _utc(datetime.fromisoformat(value))


class SQLiteRealWriteAuthorizationRepository:
    """Persistencia transaccional para autorizaciones reales de un solo uso."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path).expanduser().resolve()

    @property
    def database_path(self) -> Path:
        return self._database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                connection.executescript(_SCHEMA)
                connection.commit()
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible inicializar las autorizaciones temporales."
            ) from error

    def issue(
        self,
        authorization: RealWriteAuthorization,
    ) -> RealWriteAuthorization:
        now = authorization.issued_at
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._expire_active_for_item(
                    connection,
                    batch_id=authorization.batch_id,
                    item_id=authorization.item_id,
                    now=now,
                )
                active_rows = connection.execute(
                    """
                    SELECT *
                      FROM real_write_authorizations
                     WHERE batch_id = ?
                       AND item_id = ?
                       AND status = 'ACTIVE'
                    """,
                    (
                        str(authorization.batch_id),
                        str(authorization.item_id),
                    ),
                ).fetchall()
                for row in active_rows:
                    revoked_at = _to_text(now)
                    connection.execute(
                        """
                        UPDATE real_write_authorizations
                           SET status = 'REVOKED',
                               revoked_at = ?
                         WHERE authorization_id = ?
                           AND status = 'ACTIVE'
                        """,
                        (revoked_at, row["authorization_id"]),
                    )
                    self._insert_event(
                        connection,
                        authorization_id=UUID(
                            str(row["authorization_id"])
                        ),
                        event_type="REVOKED",
                        batch_id=UUID(str(row["batch_id"])),
                        item_id=UUID(str(row["item_id"])),
                        contract_number=str(row["contract_number"]),
                        dependency=str(row["dependency"]),
                        actor_username=str(row["actor_username"]),
                        actor_user_id=row["actor_user_id"],
                        recorded_at=now,
                        reason="REPLACED_BY_NEW_AUTHORIZATION",
                        metadata={
                            "replacement_authorization_id": str(
                                authorization.authorization_id
                            )
                        },
                    )

                connection.execute(
                    """
                    INSERT INTO real_write_authorizations (
                        authorization_id,
                        token_hash,
                        batch_id,
                        item_id,
                        contract_number,
                        contract_identity,
                        dependency,
                        dependency_identity,
                        actor_username,
                        actor_identity,
                        actor_user_id,
                        status,
                        issued_at,
                        expires_at,
                        consumed_at,
                        consumed_correlation_id,
                        revoked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
                    """,
                    (
                        str(authorization.authorization_id),
                        authorization.token_hash,
                        str(authorization.batch_id),
                        str(authorization.item_id),
                        authorization.contract_number,
                        _identity(authorization.contract_number),
                        authorization.dependency,
                        _identity(authorization.dependency),
                        authorization.actor_username,
                        _identity(authorization.actor_username),
                        authorization.actor_user_id,
                        authorization.status.value,
                        _to_text(authorization.issued_at),
                        _to_text(authorization.expires_at),
                    ),
                )
                self._insert_event(
                    connection,
                    authorization_id=authorization.authorization_id,
                    event_type="ISSUED",
                    batch_id=authorization.batch_id,
                    item_id=authorization.item_id,
                    contract_number=authorization.contract_number,
                    dependency=authorization.dependency,
                    actor_username=authorization.actor_username,
                    actor_user_id=authorization.actor_user_id,
                    recorded_at=authorization.issued_at,
                    metadata={
                        "expires_at": authorization.expires_at.isoformat(),
                        "single_use": True,
                    },
                )
                connection.commit()
        except sqlite3.IntegrityError as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible emitir una autorización temporal única."
            ) from error
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible persistir la autorización temporal."
            ) from error

        stored = self._get_by_id(authorization.authorization_id)
        if stored is None:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible recuperar la autorización emitida."
            )
        return stored

    def get_latest(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
    ) -> RealWriteAuthorization | None:
        normalized_now = _utc(now)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT *
                      FROM real_write_authorizations
                     WHERE batch_id = ?
                       AND item_id = ?
                       AND actor_identity = ?
                       AND (
                            actor_user_id = ?
                            OR (actor_user_id IS NULL AND ? IS NULL)
                       )
                     ORDER BY issued_at DESC
                     LIMIT 1
                    """,
                    (
                        str(batch_id),
                        str(item_id),
                        _identity(actor_username),
                        actor_user_id,
                        actor_user_id,
                    ),
                ).fetchone()
                if row is None:
                    connection.commit()
                    return None
                row = self._expire_row_if_needed(
                    connection,
                    row=row,
                    now=normalized_now,
                )
                connection.commit()
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible consultar la autorización temporal."
            ) from error
        return self._to_domain(row)

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
        normalized_now = _utc(now)
        pending_error: Exception | None = None
        consumed_id: UUID | None = None

        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT *
                      FROM real_write_authorizations
                     WHERE token_hash = ?
                     LIMIT 1
                    """,
                    (str(token_hash).strip().lower(),),
                ).fetchone()

                if row is None:
                    self._insert_event(
                        connection,
                        authorization_id=None,
                        event_type="REJECTED",
                        batch_id=batch_id,
                        item_id=item_id,
                        contract_number=contract_number,
                        dependency=dependency,
                        actor_username=actor_username,
                        actor_user_id=actor_user_id,
                        recorded_at=normalized_now,
                        correlation_id=correlation_id,
                        reason="INVALID_TOKEN",
                    )
                    pending_error = RealWriteAuthorizationInvalidError()
                elif not self._context_matches(
                    row,
                    batch_id=batch_id,
                    item_id=item_id,
                    contract_number=contract_number,
                    dependency=dependency,
                    actor_username=actor_username,
                    actor_user_id=actor_user_id,
                ):
                    authorization_id = UUID(str(row["authorization_id"]))
                    self._insert_event(
                        connection,
                        authorization_id=authorization_id,
                        event_type="REJECTED",
                        batch_id=batch_id,
                        item_id=item_id,
                        contract_number=contract_number,
                        dependency=dependency,
                        actor_username=actor_username,
                        actor_user_id=actor_user_id,
                        recorded_at=normalized_now,
                        correlation_id=correlation_id,
                        reason="CONTEXT_MISMATCH",
                    )
                    pending_error = RealWriteAuthorizationContextError()
                else:
                    row = self._expire_row_if_needed(
                        connection,
                        row=row,
                        now=normalized_now,
                    )
                    authorization_id = UUID(str(row["authorization_id"]))
                    status = RealWriteAuthorizationStatus(
                        str(row["status"])
                    )
                    if status is RealWriteAuthorizationStatus.EXPIRED:
                        self._insert_event(
                            connection,
                            authorization_id=authorization_id,
                            event_type="REJECTED",
                            batch_id=batch_id,
                            item_id=item_id,
                            contract_number=contract_number,
                            dependency=dependency,
                            actor_username=actor_username,
                            actor_user_id=actor_user_id,
                            recorded_at=normalized_now,
                            correlation_id=correlation_id,
                            reason="EXPIRED",
                        )
                        pending_error = (
                            RealWriteAuthorizationExpiredError(
                                authorization_id
                            )
                        )
                    elif status is RealWriteAuthorizationStatus.CONSUMED:
                        self._insert_event(
                            connection,
                            authorization_id=authorization_id,
                            event_type="REJECTED",
                            batch_id=batch_id,
                            item_id=item_id,
                            contract_number=contract_number,
                            dependency=dependency,
                            actor_username=actor_username,
                            actor_user_id=actor_user_id,
                            recorded_at=normalized_now,
                            correlation_id=correlation_id,
                            reason="ALREADY_CONSUMED",
                        )
                        pending_error = (
                            RealWriteAuthorizationConsumedError(
                                authorization_id
                            )
                        )
                    elif status is RealWriteAuthorizationStatus.REVOKED:
                        self._insert_event(
                            connection,
                            authorization_id=authorization_id,
                            event_type="REJECTED",
                            batch_id=batch_id,
                            item_id=item_id,
                            contract_number=contract_number,
                            dependency=dependency,
                            actor_username=actor_username,
                            actor_user_id=actor_user_id,
                            recorded_at=normalized_now,
                            correlation_id=correlation_id,
                            reason="REVOKED",
                        )
                        pending_error = (
                            RealWriteAuthorizationRevokedError(
                                authorization_id
                            )
                        )
                    else:
                        cursor = connection.execute(
                            """
                            UPDATE real_write_authorizations
                               SET status = 'CONSUMED',
                                   consumed_at = ?,
                                   consumed_correlation_id = ?
                             WHERE authorization_id = ?
                               AND status = 'ACTIVE'
                               AND consumed_at IS NULL
                            """,
                            (
                                _to_text(normalized_now),
                                str(correlation_id),
                                str(authorization_id),
                            ),
                        )
                        if cursor.rowcount != 1:
                            self._insert_event(
                                connection,
                                authorization_id=authorization_id,
                                event_type="REJECTED",
                                batch_id=batch_id,
                                item_id=item_id,
                                contract_number=contract_number,
                                dependency=dependency,
                                actor_username=actor_username,
                                actor_user_id=actor_user_id,
                                recorded_at=normalized_now,
                                correlation_id=correlation_id,
                                reason="CONCURRENT_CONSUMPTION",
                            )
                            pending_error = (
                                RealWriteAuthorizationConsumedError(
                                    authorization_id
                                )
                            )
                        else:
                            self._insert_event(
                                connection,
                                authorization_id=authorization_id,
                                event_type="CONSUMED",
                                batch_id=batch_id,
                                item_id=item_id,
                                contract_number=contract_number,
                                dependency=dependency,
                                actor_username=actor_username,
                                actor_user_id=actor_user_id,
                                recorded_at=normalized_now,
                                correlation_id=correlation_id,
                                metadata={"single_use": True},
                            )
                            consumed_id = authorization_id
                connection.commit()
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible consumir la autorización temporal."
            ) from error

        if pending_error is not None:
            raise pending_error
        if consumed_id is None:
            raise RealWriteAuthorizationRepositoryError(
                "La autorización no pudo consumirse de forma atómica."
            )

        stored = self._get_by_id(consumed_id)
        if stored is None:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible recuperar la autorización consumida."
            )
        return stored

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
        normalized_now = _utc(now)
        pending_error: Exception | None = None
        revoked_id: UUID | None = None

        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT *
                      FROM real_write_authorizations
                     WHERE batch_id = ?
                       AND item_id = ?
                       AND actor_identity = ?
                       AND (
                            actor_user_id = ?
                            OR (actor_user_id IS NULL AND ? IS NULL)
                       )
                     ORDER BY issued_at DESC
                     LIMIT 1
                    """,
                    (
                        str(batch_id),
                        str(item_id),
                        _identity(actor_username),
                        actor_user_id,
                        actor_user_id,
                    ),
                ).fetchone()

                if row is None:
                    self._insert_event(
                        connection,
                        authorization_id=None,
                        event_type="REJECTED",
                        batch_id=batch_id,
                        item_id=item_id,
                        contract_number=contract_number,
                        dependency=dependency,
                        actor_username=actor_username,
                        actor_user_id=actor_user_id,
                        recorded_at=normalized_now,
                        reason="REVOCATION_NOT_FOUND",
                    )
                    pending_error = RealWriteAuthorizationNotFoundError()
                elif not self._context_matches(
                    row,
                    batch_id=batch_id,
                    item_id=item_id,
                    contract_number=contract_number,
                    dependency=dependency,
                    actor_username=actor_username,
                    actor_user_id=actor_user_id,
                ):
                    authorization_id = UUID(str(row["authorization_id"]))
                    self._insert_event(
                        connection,
                        authorization_id=authorization_id,
                        event_type="REJECTED",
                        batch_id=batch_id,
                        item_id=item_id,
                        contract_number=contract_number,
                        dependency=dependency,
                        actor_username=actor_username,
                        actor_user_id=actor_user_id,
                        recorded_at=normalized_now,
                        reason="REVOCATION_CONTEXT_MISMATCH",
                    )
                    pending_error = RealWriteAuthorizationContextError()
                else:
                    row = self._expire_row_if_needed(
                        connection,
                        row=row,
                        now=normalized_now,
                    )
                    authorization_id = UUID(str(row["authorization_id"]))
                    current_status = RealWriteAuthorizationStatus(
                        str(row["status"])
                    )
                    if current_status is RealWriteAuthorizationStatus.EXPIRED:
                        pending_error = RealWriteAuthorizationExpiredError(
                            authorization_id
                        )
                    elif current_status is RealWriteAuthorizationStatus.CONSUMED:
                        pending_error = RealWriteAuthorizationConsumedError(
                            authorization_id
                        )
                    elif current_status is RealWriteAuthorizationStatus.REVOKED:
                        pending_error = RealWriteAuthorizationRevokedError(
                            authorization_id
                        )
                    else:
                        cursor = connection.execute(
                            """
                            UPDATE real_write_authorizations
                               SET status = 'REVOKED',
                                   revoked_at = ?
                             WHERE authorization_id = ?
                               AND status = 'ACTIVE'
                            """,
                            (
                                _to_text(normalized_now),
                                str(authorization_id),
                            ),
                        )
                        if cursor.rowcount != 1:
                            pending_error = (
                                RealWriteAuthorizationRevokedError(
                                    authorization_id
                                )
                            )
                        else:
                            self._insert_event(
                                connection,
                                authorization_id=authorization_id,
                                event_type="REVOKED",
                                batch_id=batch_id,
                                item_id=item_id,
                                contract_number=contract_number,
                                dependency=dependency,
                                actor_username=actor_username,
                                actor_user_id=actor_user_id,
                                recorded_at=normalized_now,
                                reason=str(reason).strip()
                                or "MANUAL_REVOCATION",
                                metadata={"manual": True},
                            )
                            revoked_id = authorization_id
                connection.commit()
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible revocar la autorización temporal."
            ) from error

        if pending_error is not None:
            raise pending_error
        if revoked_id is None:
            raise RealWriteAuthorizationRepositoryError(
                "La autorización temporal no pudo revocarse."
            )

        stored = self._get_by_id(revoked_id)
        if stored is None:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible recuperar la autorización revocada."
            )
        return stored

    def expire_due(
        self,
        *,
        now: datetime,
        limit: int = 500,
    ) -> int:
        normalized_now = _utc(now)
        normalized_limit = max(1, min(int(limit), 5000))
        expired_count = 0

        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(
                    """
                    SELECT *
                      FROM real_write_authorizations
                     WHERE status = 'ACTIVE'
                       AND expires_at <= ?
                     ORDER BY expires_at ASC
                     LIMIT ?
                    """,
                    (_to_text(normalized_now), normalized_limit),
                ).fetchall()
                for row in rows:
                    before = connection.total_changes
                    self._mark_expired(
                        connection,
                        row=row,
                        now=normalized_now,
                    )
                    if connection.total_changes > before:
                        expired_count += 1
                connection.commit()
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible limpiar autorizaciones temporales vencidas."
            ) from error

        return expired_count

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
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._insert_event(
                    connection,
                    authorization_id=authorization_id,
                    event_type="REJECTED",
                    batch_id=batch_id,
                    item_id=item_id,
                    contract_number=contract_number,
                    dependency=dependency,
                    actor_username=actor_username,
                    actor_user_id=actor_user_id,
                    recorded_at=recorded_at,
                    correlation_id=correlation_id,
                    reason=reason,
                )
                connection.commit()
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible auditar el rechazo de autorización."
            ) from error

    def list_events(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        authorization_id: UUID | None = None,
    ) -> tuple[RealWriteAuthorizationEvent, ...]:
        query = """
            SELECT *
              FROM real_write_authorization_events
             WHERE batch_id = ?
               AND item_id = ?
        """
        parameters: list[Any] = [str(batch_id), str(item_id)]
        if authorization_id is not None:
            query += " AND authorization_id = ?"
            parameters.append(str(authorization_id))
        query += " ORDER BY recorded_at ASC, rowid ASC"

        try:
            with self._connect() as connection:
                rows = connection.execute(
                    query,
                    tuple(parameters),
                ).fetchall()
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible consultar la auditoría de autorizaciones."
            ) from error
        return tuple(self._event_to_domain(row) for row in rows)

    def _get_by_id(
        self,
        authorization_id: UUID,
    ) -> RealWriteAuthorization | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT *
                      FROM real_write_authorizations
                     WHERE authorization_id = ?
                    """,
                    (str(authorization_id),),
                ).fetchone()
        except sqlite3.Error as error:
            raise RealWriteAuthorizationRepositoryError(
                "No fue posible recuperar la autorización temporal."
            ) from error
        return self._to_domain(row) if row is not None else None

    def _expire_active_for_item(
        self,
        connection: sqlite3.Connection,
        *,
        batch_id: UUID,
        item_id: UUID,
        now: datetime,
    ) -> None:
        rows = connection.execute(
            """
            SELECT *
              FROM real_write_authorizations
             WHERE batch_id = ?
               AND item_id = ?
               AND status = 'ACTIVE'
               AND expires_at <= ?
            """,
            (str(batch_id), str(item_id), _to_text(now)),
        ).fetchall()
        for row in rows:
            self._mark_expired(connection, row=row, now=now)

    def _expire_row_if_needed(
        self,
        connection: sqlite3.Connection,
        *,
        row: sqlite3.Row,
        now: datetime,
    ) -> sqlite3.Row:
        status = RealWriteAuthorizationStatus(str(row["status"]))
        expires_at = _from_text(str(row["expires_at"]))
        if (
            status is RealWriteAuthorizationStatus.ACTIVE
            and expires_at is not None
            and expires_at <= now
        ):
            self._mark_expired(connection, row=row, now=now)
            refreshed = connection.execute(
                """
                SELECT *
                  FROM real_write_authorizations
                 WHERE authorization_id = ?
                """,
                (row["authorization_id"],),
            ).fetchone()
            if refreshed is None:
                raise RealWriteAuthorizationRepositoryError(
                    "La autorización expirada no pudo recuperarse."
                )
            return refreshed
        return row

    def _mark_expired(
        self,
        connection: sqlite3.Connection,
        *,
        row: sqlite3.Row,
        now: datetime,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE real_write_authorizations
               SET status = 'EXPIRED'
             WHERE authorization_id = ?
               AND status = 'ACTIVE'
            """,
            (row["authorization_id"],),
        )
        if cursor.rowcount != 1:
            return
        self._insert_event(
            connection,
            authorization_id=UUID(str(row["authorization_id"])),
            event_type="EXPIRED",
            batch_id=UUID(str(row["batch_id"])),
            item_id=UUID(str(row["item_id"])),
            contract_number=str(row["contract_number"]),
            dependency=str(row["dependency"]),
            actor_username=str(row["actor_username"]),
            actor_user_id=row["actor_user_id"],
            recorded_at=now,
            reason="TTL_EXPIRED",
        )

    @staticmethod
    def _context_matches(
        row: sqlite3.Row,
        *,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
    ) -> bool:
        same_user_id = (
            row["actor_user_id"] == actor_user_id
            or (
                row["actor_user_id"] is None
                and actor_user_id is None
            )
        )
        return (
            str(row["batch_id"]) == str(batch_id)
            and str(row["item_id"]) == str(item_id)
            and str(row["contract_identity"])
            == _identity(contract_number)
            and str(row["dependency_identity"])
            == _identity(dependency)
            and str(row["actor_identity"])
            == _identity(actor_username)
            and same_user_id
        )

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        *,
        authorization_id: UUID | None,
        event_type: str,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        recorded_at: datetime,
        correlation_id: UUID | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO real_write_authorization_events (
                event_id,
                authorization_id,
                event_type,
                batch_id,
                item_id,
                contract_number,
                dependency,
                actor_username,
                actor_user_id,
                recorded_at,
                correlation_id,
                reason,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                (
                    str(authorization_id)
                    if authorization_id is not None
                    else None
                ),
                str(event_type).strip().upper(),
                str(batch_id),
                str(item_id),
                str(contract_number).strip(),
                " ".join(str(dependency).split()),
                str(actor_username).strip(),
                actor_user_id,
                _to_text(recorded_at),
                (
                    str(correlation_id)
                    if correlation_id is not None
                    else None
                ),
                None if reason is None else str(reason).strip(),
                json.dumps(
                    dict(metadata or {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            timeout=30,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def _to_domain(row: sqlite3.Row) -> RealWriteAuthorization:
        consumed_correlation = row["consumed_correlation_id"]
        return RealWriteAuthorization(
            authorization_id=UUID(str(row["authorization_id"])),
            token_hash=str(row["token_hash"]),
            batch_id=UUID(str(row["batch_id"])),
            item_id=UUID(str(row["item_id"])),
            contract_number=str(row["contract_number"]),
            dependency=str(row["dependency"]),
            actor_username=str(row["actor_username"]),
            actor_user_id=row["actor_user_id"],
            status=RealWriteAuthorizationStatus(str(row["status"])),
            issued_at=_from_text(str(row["issued_at"])),
            expires_at=_from_text(str(row["expires_at"])),
            consumed_at=_from_text(row["consumed_at"]),
            consumed_correlation_id=(
                UUID(str(consumed_correlation))
                if consumed_correlation
                else None
            ),
            revoked_at=_from_text(row["revoked_at"]),
        )

    @staticmethod
    def _event_to_domain(
        row: sqlite3.Row,
    ) -> RealWriteAuthorizationEvent:
        authorization_id = row["authorization_id"]
        correlation_id = row["correlation_id"]
        try:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except json.JSONDecodeError:
            metadata = {}
        return RealWriteAuthorizationEvent(
            event_id=UUID(str(row["event_id"])),
            authorization_id=(
                UUID(str(authorization_id))
                if authorization_id
                else None
            ),
            event_type=str(row["event_type"]),
            batch_id=UUID(str(row["batch_id"])),
            item_id=UUID(str(row["item_id"])),
            contract_number=str(row["contract_number"]),
            dependency=str(row["dependency"]),
            actor_username=str(row["actor_username"]),
            actor_user_id=row["actor_user_id"],
            recorded_at=_from_text(str(row["recorded_at"])),
            correlation_id=(
                UUID(str(correlation_id))
                if correlation_id
                else None
            ),
            reason=row["reason"],
            metadata=metadata,
        )
