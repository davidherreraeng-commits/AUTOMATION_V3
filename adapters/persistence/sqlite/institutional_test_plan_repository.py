from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from application.dto.institutional_test_plan import (
    InstitutionalTestPlan,
    InstitutionalTestPlanEvent,
)
from domain.enums.institutional_test_plan_status import (
    InstitutionalTestPlanStatus,
)
from domain.errors.institutional_test_plan_errors import (
    InstitutionalTestPlanCancelledError,
    InstitutionalTestPlanConsumedError,
    InstitutionalTestPlanContextError,
    InstitutionalTestPlanDiagnosticExpiredError,
    InstitutionalTestPlanDiagnosticRequiredError,
    InstitutionalTestPlanExpiredError,
    InstitutionalTestPlanNotArmedError,
    InstitutionalTestPlanNotFoundError,
    InstitutionalTestPlanRepositoryError,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS institutional_test_plans (
    plan_id TEXT PRIMARY KEY,
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
    created_at TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    max_executions INTEGER NOT NULL DEFAULT 1,
    execution_count INTEGER NOT NULL DEFAULT 0,
    diagnostic_checked_at TEXT,
    diagnostic_success INTEGER,
    diagnostic_code TEXT,
    diagnostic_message TEXT,
    diagnostic_authenticated INTEGER NOT NULL DEFAULT 0,
    diagnostic_contracting_menu_found INTEGER NOT NULL DEFAULT 0,
    diagnostic_enter_contract_found INTEGER NOT NULL DEFAULT 0,
    diagnostic_assistant_access_found INTEGER NOT NULL DEFAULT 0,
    diagnostic_duration_ms INTEGER,
    armed_at TEXT,
    consumed_at TEXT,
    consumed_correlation_id TEXT,
    cancelled_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_institutional_test_plans_context
ON institutional_test_plans(
    batch_id,
    item_id,
    actor_identity,
    created_at DESC
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_institutional_plan_per_item
ON institutional_test_plans(batch_id, item_id)
WHERE status IN ('DRAFT', 'READY', 'ARMED');

CREATE TABLE IF NOT EXISTS institutional_test_plan_events (
    event_id TEXT PRIMARY KEY,
    plan_id TEXT,
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

CREATE INDEX IF NOT EXISTS idx_institutional_test_plan_events_context
ON institutional_test_plan_events(batch_id, item_id, recorded_at ASC);
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


class SQLiteInstitutionalTestPlanRepository:
    """Persistencia transaccional para planes institucionales de un uso."""

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
            raise InstitutionalTestPlanRepositoryError(
                "No fue posible inicializar los planes institucionales."
            ) from error

    def create(self, plan: InstitutionalTestPlan) -> InstitutionalTestPlan:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._expire_due_in_connection(connection, now=plan.created_at)
                active = connection.execute(
                    """
                    SELECT * FROM institutional_test_plans
                     WHERE batch_id = ?
                       AND item_id = ?
                       AND status IN ('DRAFT', 'READY', 'ARMED')
                    """,
                    (str(plan.batch_id), str(plan.item_id)),
                ).fetchall()
                for row in active:
                    connection.execute(
                        """
                        UPDATE institutional_test_plans
                           SET status = 'CANCELLED', cancelled_at = ?
                         WHERE plan_id = ?
                        """,
                        (_to_text(plan.created_at), row["plan_id"]),
                    )
                    self._insert_event(
                        connection,
                        plan_id=UUID(str(row["plan_id"])),
                        event_type="CANCELLED",
                        batch_id=UUID(str(row["batch_id"])),
                        item_id=UUID(str(row["item_id"])),
                        contract_number=str(row["contract_number"]),
                        dependency=str(row["dependency"]),
                        actor_username=str(row["actor_username"]),
                        actor_user_id=row["actor_user_id"],
                        recorded_at=plan.created_at,
                        reason="REPLACED_BY_NEW_PLAN",
                        metadata={"replacement_plan_id": str(plan.plan_id)},
                    )

                connection.execute(
                    """
                    INSERT INTO institutional_test_plans (
                        plan_id, batch_id, item_id, contract_number,
                        contract_identity, dependency, dependency_identity,
                        actor_username, actor_identity, actor_user_id,
                        status, created_at, starts_at, expires_at,
                        max_executions, execution_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(plan.plan_id),
                        str(plan.batch_id),
                        str(plan.item_id),
                        plan.contract_number,
                        _identity(plan.contract_number),
                        plan.dependency,
                        _identity(plan.dependency),
                        plan.actor_username,
                        _identity(plan.actor_username),
                        plan.actor_user_id,
                        plan.status.value,
                        _to_text(plan.created_at),
                        _to_text(plan.starts_at),
                        _to_text(plan.expires_at),
                        plan.max_executions,
                        plan.execution_count,
                    ),
                )
                self._insert_event(
                    connection,
                    plan_id=plan.plan_id,
                    event_type="CREATED",
                    batch_id=plan.batch_id,
                    item_id=plan.item_id,
                    contract_number=plan.contract_number,
                    dependency=plan.dependency,
                    actor_username=plan.actor_username,
                    actor_user_id=plan.actor_user_id,
                    recorded_at=plan.created_at,
                    metadata={
                        "starts_at": plan.starts_at.isoformat(),
                        "expires_at": plan.expires_at.isoformat(),
                        "max_executions": 1,
                    },
                )
                connection.commit()
        except sqlite3.IntegrityError as error:
            raise InstitutionalTestPlanRepositoryError(
                "No fue posible crear un plan institucional único."
            ) from error
        except sqlite3.Error as error:
            raise InstitutionalTestPlanRepositoryError(
                "No fue posible persistir el plan institucional."
            ) from error
        return self._require_by_id(plan.plan_id)

    def get_latest(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
    ) -> InstitutionalTestPlan | None:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._expire_due_in_connection(connection, now=now)
                row = connection.execute(
                    """
                    SELECT * FROM institutional_test_plans
                     WHERE batch_id = ?
                       AND item_id = ?
                       AND actor_identity = ?
                       AND (
                           actor_user_id = ?
                           OR (actor_user_id IS NULL AND ? IS NULL)
                       )
                     ORDER BY created_at DESC
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
                connection.commit()
        except sqlite3.Error as error:
            raise InstitutionalTestPlanRepositoryError(
                "No fue posible consultar el plan institucional."
            ) from error
        return self._to_domain(row) if row is not None else None

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
        with self._transaction() as connection:
            row = self._require_context(
                connection,
                plan_id=plan_id,
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                now=checked_at,
            )
            status = InstitutionalTestPlanStatus(str(row["status"]))
            if status in {
                InstitutionalTestPlanStatus.CANCELLED,
                InstitutionalTestPlanStatus.CONSUMED,
                InstitutionalTestPlanStatus.EXPIRED,
            }:
                self._raise_status(status, plan_id)
            next_status = (
                InstitutionalTestPlanStatus.READY
                if success
                else InstitutionalTestPlanStatus.DRAFT
            )
            connection.execute(
                """
                UPDATE institutional_test_plans
                   SET status = ?,
                       diagnostic_checked_at = ?,
                       diagnostic_success = ?,
                       diagnostic_code = ?,
                       diagnostic_message = ?,
                       diagnostic_authenticated = ?,
                       diagnostic_contracting_menu_found = ?,
                       diagnostic_enter_contract_found = ?,
                       diagnostic_assistant_access_found = ?,
                       diagnostic_duration_ms = ?,
                       armed_at = NULL
                 WHERE plan_id = ?
                """,
                (
                    next_status.value,
                    _to_text(checked_at),
                    1 if success else 0,
                    str(code).strip().upper(),
                    str(message).strip(),
                    1 if authenticated else 0,
                    1 if contracting_menu_found else 0,
                    1 if enter_contract_found else 0,
                    1 if assistant_access_found else 0,
                    max(0, int(duration_ms)),
                    str(plan_id),
                ),
            )
            self._insert_event(
                connection,
                plan_id=plan_id,
                event_type="DIAGNOSTIC_PASSED" if success else "DIAGNOSTIC_FAILED",
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                recorded_at=checked_at,
                reason=None if success else str(code).strip().upper(),
                metadata={
                    "code": str(code).strip().upper(),
                    "message": str(message).strip(),
                    "authenticated": bool(authenticated),
                    "contracting_menu_found": bool(contracting_menu_found),
                    "enter_contract_found": bool(enter_contract_found),
                    "assistant_access_found": bool(assistant_access_found),
                    "duration_ms": max(0, int(duration_ms)),
                    "read_only": True,
                },
            )
        return self._require_by_id(plan_id)

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
        with self._transaction() as connection:
            row = self._require_context(
                connection,
                plan_id=plan_id,
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                now=now,
            )
            status = InstitutionalTestPlanStatus(str(row["status"]))
            if status in {
                InstitutionalTestPlanStatus.CANCELLED,
                InstitutionalTestPlanStatus.CONSUMED,
                InstitutionalTestPlanStatus.EXPIRED,
            }:
                self._raise_status(status, plan_id)
            checked_at = _from_text(row["diagnostic_checked_at"])
            if not bool(row["diagnostic_success"]) or checked_at is None:
                raise InstitutionalTestPlanDiagnosticRequiredError()
            if checked_at < _utc(diagnostic_not_before):
                raise InstitutionalTestPlanDiagnosticExpiredError()
            connection.execute(
                """
                UPDATE institutional_test_plans
                   SET status = 'ARMED', armed_at = ?
                 WHERE plan_id = ?
                """,
                (_to_text(now), str(plan_id)),
            )
            self._insert_event(
                connection,
                plan_id=plan_id,
                event_type="ARMED",
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                recorded_at=now,
                metadata={"max_executions": 1},
            )
        return self._require_by_id(plan_id)

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
        with self._transaction() as connection:
            row = self._require_context(
                connection,
                plan_id=plan_id,
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                now=now,
            )
            status = InstitutionalTestPlanStatus(str(row["status"]))
            if status is not InstitutionalTestPlanStatus.ARMED:
                if status in {
                    InstitutionalTestPlanStatus.CANCELLED,
                    InstitutionalTestPlanStatus.CONSUMED,
                    InstitutionalTestPlanStatus.EXPIRED,
                }:
                    self._raise_status(status, plan_id)
                raise InstitutionalTestPlanNotArmedError()
            cursor = connection.execute(
                """
                UPDATE institutional_test_plans
                   SET status = 'CONSUMED',
                       execution_count = execution_count + 1,
                       consumed_at = ?,
                       consumed_correlation_id = ?
                 WHERE plan_id = ?
                   AND status = 'ARMED'
                   AND execution_count = 0
                """,
                (_to_text(now), str(correlation_id), str(plan_id)),
            )
            if cursor.rowcount != 1:
                raise InstitutionalTestPlanConsumedError(plan_id)
            self._insert_event(
                connection,
                plan_id=plan_id,
                event_type="CONSUMED",
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                recorded_at=now,
                correlation_id=correlation_id,
                metadata={"execution_count": 1},
            )
        return self._require_by_id(plan_id)

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
        with self._transaction() as connection:
            row = self._require_context(
                connection,
                plan_id=plan_id,
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                now=now,
            )
            status = InstitutionalTestPlanStatus(str(row["status"]))
            if status in {
                InstitutionalTestPlanStatus.CONSUMED,
                InstitutionalTestPlanStatus.CANCELLED,
                InstitutionalTestPlanStatus.EXPIRED,
            }:
                self._raise_status(status, plan_id)
            connection.execute(
                """
                UPDATE institutional_test_plans
                   SET status = 'CANCELLED', cancelled_at = ?
                 WHERE plan_id = ?
                """,
                (_to_text(now), str(plan_id)),
            )
            self._insert_event(
                connection,
                plan_id=plan_id,
                event_type="CANCELLED",
                batch_id=batch_id,
                item_id=item_id,
                contract_number=contract_number,
                dependency=dependency,
                actor_username=actor_username,
                actor_user_id=actor_user_id,
                recorded_at=now,
                reason=str(reason).strip() or "MANUAL_CANCELLATION",
            )
        return self._require_by_id(plan_id)

    def expire_due(self, *, now: datetime, limit: int = 500) -> int:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                count = self._expire_due_in_connection(
                    connection,
                    now=now,
                    limit=limit,
                )
                connection.commit()
                return count
        except sqlite3.Error as error:
            raise InstitutionalTestPlanRepositoryError(
                "No fue posible expirar los planes institucionales."
            ) from error

    def list_events(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        plan_id: UUID | None = None,
    ) -> tuple[InstitutionalTestPlanEvent, ...]:
        query = """
            SELECT * FROM institutional_test_plan_events
             WHERE batch_id = ? AND item_id = ?
        """
        parameters: list[Any] = [str(batch_id), str(item_id)]
        if plan_id is not None:
            query += " AND plan_id = ?"
            parameters.append(str(plan_id))
        query += " ORDER BY recorded_at ASC, rowid ASC"
        try:
            with self._connect() as connection:
                rows = connection.execute(query, tuple(parameters)).fetchall()
        except sqlite3.Error as error:
            raise InstitutionalTestPlanRepositoryError(
                "No fue posible consultar los eventos del plan."
            ) from error
        return tuple(self._event_to_domain(row) for row in rows)

    def _require_context(
        self,
        connection: sqlite3.Connection,
        *,
        plan_id: UUID,
        batch_id: UUID,
        item_id: UUID,
        contract_number: str,
        dependency: str,
        actor_username: str,
        actor_user_id: int | None,
        now: datetime,
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM institutional_test_plans WHERE plan_id = ?",
            (str(plan_id),),
        ).fetchone()
        if row is None:
            raise InstitutionalTestPlanNotFoundError()
        if (
            str(row["batch_id"]) != str(batch_id)
            or str(row["item_id"]) != str(item_id)
            or str(row["contract_identity"]) != _identity(contract_number)
            or str(row["dependency_identity"]) != _identity(dependency)
            or str(row["actor_identity"]) != _identity(actor_username)
            or not (
                row["actor_user_id"] == actor_user_id
                or (row["actor_user_id"] is None and actor_user_id is None)
            )
        ):
            raise InstitutionalTestPlanContextError()
        expires_at = _from_text(row["expires_at"])
        if (
            InstitutionalTestPlanStatus(str(row["status"]))
            in {
                InstitutionalTestPlanStatus.DRAFT,
                InstitutionalTestPlanStatus.READY,
                InstitutionalTestPlanStatus.ARMED,
            }
            and expires_at is not None
            and expires_at <= _utc(now)
        ):
            self._mark_expired(connection, row=row, now=now)
            raise InstitutionalTestPlanExpiredError(plan_id)
        return row

    def _expire_due_in_connection(
        self,
        connection: sqlite3.Connection,
        *,
        now: datetime,
        limit: int = 500,
    ) -> int:
        rows = connection.execute(
            """
            SELECT * FROM institutional_test_plans
             WHERE status IN ('DRAFT', 'READY', 'ARMED')
               AND expires_at <= ?
             ORDER BY expires_at ASC
             LIMIT ?
            """,
            (_to_text(now), max(1, min(int(limit), 5000))),
        ).fetchall()
        count = 0
        for row in rows:
            before = connection.total_changes
            self._mark_expired(connection, row=row, now=now)
            if connection.total_changes > before:
                count += 1
        return count

    def _mark_expired(
        self,
        connection: sqlite3.Connection,
        *,
        row: sqlite3.Row,
        now: datetime,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE institutional_test_plans
               SET status = 'EXPIRED'
             WHERE plan_id = ?
               AND status IN ('DRAFT', 'READY', 'ARMED')
            """,
            (row["plan_id"],),
        )
        if cursor.rowcount != 1:
            return
        self._insert_event(
            connection,
            plan_id=UUID(str(row["plan_id"])),
            event_type="EXPIRED",
            batch_id=UUID(str(row["batch_id"])),
            item_id=UUID(str(row["item_id"])),
            contract_number=str(row["contract_number"]),
            dependency=str(row["dependency"]),
            actor_username=str(row["actor_username"]),
            actor_user_id=row["actor_user_id"],
            recorded_at=now,
            reason="WINDOW_EXPIRED",
        )

    def _require_by_id(self, plan_id: UUID) -> InstitutionalTestPlan:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM institutional_test_plans WHERE plan_id = ?",
                    (str(plan_id),),
                ).fetchone()
        except sqlite3.Error as error:
            raise InstitutionalTestPlanRepositoryError(
                "No fue posible recuperar el plan institucional."
            ) from error
        if row is None:
            raise InstitutionalTestPlanNotFoundError()
        return self._to_domain(row)

    @staticmethod
    def _raise_status(
        status: InstitutionalTestPlanStatus,
        plan_id: UUID,
    ) -> None:
        if status is InstitutionalTestPlanStatus.EXPIRED:
            raise InstitutionalTestPlanExpiredError(plan_id)
        if status is InstitutionalTestPlanStatus.CANCELLED:
            raise InstitutionalTestPlanCancelledError(plan_id)
        if status is InstitutionalTestPlanStatus.CONSUMED:
            raise InstitutionalTestPlanConsumedError(plan_id)

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        *,
        plan_id: UUID | None,
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
            INSERT INTO institutional_test_plan_events (
                event_id, plan_id, event_type, batch_id, item_id,
                contract_number, dependency, actor_username, actor_user_id,
                recorded_at, correlation_id, reason, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                str(plan_id) if plan_id is not None else None,
                str(event_type).strip().upper(),
                str(batch_id),
                str(item_id),
                contract_number,
                dependency,
                actor_username,
                actor_user_id,
                _to_text(recorded_at),
                str(correlation_id) if correlation_id else None,
                reason,
                json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
            ),
        )

    def _transaction(self):
        class _Transaction:
            def __init__(self, outer):
                self.outer = outer
                self.connection = None

            def __enter__(self):
                self.connection = self.outer._connect()
                self.connection.execute("BEGIN IMMEDIATE")
                return self.connection

            def __exit__(self, exc_type, exc, tb):
                assert self.connection is not None
                try:
                    if exc_type is None:
                        self.connection.commit()
                    else:
                        self.connection.rollback()
                finally:
                    self.connection.close()
                return False

        return _Transaction(self)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def _to_domain(row: sqlite3.Row) -> InstitutionalTestPlan:
        return InstitutionalTestPlan(
            plan_id=UUID(str(row["plan_id"])),
            batch_id=UUID(str(row["batch_id"])),
            item_id=UUID(str(row["item_id"])),
            contract_number=str(row["contract_number"]),
            dependency=str(row["dependency"]),
            actor_username=str(row["actor_username"]),
            actor_user_id=row["actor_user_id"],
            status=InstitutionalTestPlanStatus(str(row["status"])),
            created_at=_from_text(str(row["created_at"])),
            starts_at=_from_text(str(row["starts_at"])),
            expires_at=_from_text(str(row["expires_at"])),
            max_executions=int(row["max_executions"]),
            execution_count=int(row["execution_count"]),
            diagnostic_checked_at=_from_text(row["diagnostic_checked_at"]),
            diagnostic_success=(
                None
                if row["diagnostic_success"] is None
                else bool(row["diagnostic_success"])
            ),
            diagnostic_code=row["diagnostic_code"],
            diagnostic_message=row["diagnostic_message"],
            diagnostic_authenticated=bool(row["diagnostic_authenticated"]),
            diagnostic_contracting_menu_found=bool(
                row["diagnostic_contracting_menu_found"]
            ),
            diagnostic_enter_contract_found=bool(
                row["diagnostic_enter_contract_found"]
            ),
            diagnostic_assistant_access_found=bool(
                row["diagnostic_assistant_access_found"]
            ),
            diagnostic_duration_ms=row["diagnostic_duration_ms"],
            armed_at=_from_text(row["armed_at"]),
            consumed_at=_from_text(row["consumed_at"]),
            consumed_correlation_id=(
                UUID(str(row["consumed_correlation_id"]))
                if row["consumed_correlation_id"]
                else None
            ),
            cancelled_at=_from_text(row["cancelled_at"]),
        )

    @staticmethod
    def _event_to_domain(row: sqlite3.Row) -> InstitutionalTestPlanEvent:
        try:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except json.JSONDecodeError:
            metadata = {}
        return InstitutionalTestPlanEvent(
            event_id=UUID(str(row["event_id"])),
            plan_id=UUID(str(row["plan_id"])) if row["plan_id"] else None,
            event_type=str(row["event_type"]),
            batch_id=UUID(str(row["batch_id"])),
            item_id=UUID(str(row["item_id"])),
            contract_number=str(row["contract_number"]),
            dependency=str(row["dependency"]),
            actor_username=str(row["actor_username"]),
            actor_user_id=row["actor_user_id"],
            recorded_at=_from_text(str(row["recorded_at"])),
            correlation_id=(
                UUID(str(row["correlation_id"]))
                if row["correlation_id"]
                else None
            ),
            reason=row["reason"],
            metadata=metadata if isinstance(metadata, dict) else {},
        )
