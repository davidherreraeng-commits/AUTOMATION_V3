from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from domain.errors.portal_credential_errors import (
    PortalCredentialsNotConfiguredError,
)
from domain.models.portal_credentials import PortalCredentials


_SCHEMA = """
CREATE TABLE IF NOT EXISTS portal_credentials (
    dependency TEXT PRIMARY KEY COLLATE NOCASE,
    portal_username TEXT NOT NULL,
    encrypted_password TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_tested_at TEXT NULL,
    last_test_success INTEGER NULL
        CHECK (last_test_success IS NULL OR last_test_success IN (0, 1)),
    last_test_code TEXT NULL
);
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class SQLitePortalCredentialRepository:
    """Persistencia SQLite de credenciales cifradas por dependencia."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path).expanduser().resolve()

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)
            connection.commit()

    def find_by_dependency(
        self,
        dependency: str,
    ) -> PortalCredentials | None:
        normalized = str(dependency).strip()
        if not normalized:
            return None

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                  FROM portal_credentials
                 WHERE dependency = ? COLLATE NOCASE
                """,
                (normalized,),
            ).fetchone()

        return self._to_domain(row) if row else None

    def upsert(
        self,
        *,
        dependency: str,
        portal_username: str,
        encrypted_password: str,
    ) -> PortalCredentials:
        normalized_dependency = str(dependency).strip()
        normalized_username = str(portal_username).strip()
        normalized_password = str(encrypted_password).strip()

        if not normalized_dependency:
            raise ValueError("La dependencia es obligatoria.")
        if not normalized_username:
            raise ValueError("El usuario del portal es obligatorio.")
        if not normalized_password:
            raise ValueError("La contraseña cifrada es obligatoria.")

        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO portal_credentials (
                    dependency,
                    portal_username,
                    encrypted_password,
                    created_at,
                    updated_at,
                    last_tested_at,
                    last_test_success,
                    last_test_code
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)
                ON CONFLICT(dependency) DO UPDATE SET
                    portal_username = excluded.portal_username,
                    encrypted_password = excluded.encrypted_password,
                    updated_at = excluded.updated_at,
                    last_tested_at = NULL,
                    last_test_success = NULL,
                    last_test_code = NULL
                """,
                (
                    normalized_dependency,
                    normalized_username,
                    normalized_password,
                    _serialize_datetime(now),
                    _serialize_datetime(now),
                ),
            )
            connection.commit()

        record = self.find_by_dependency(normalized_dependency)
        if record is None:
            raise RuntimeError(
                "No fue posible recuperar las credenciales guardadas."
            )
        return record

    def record_test_result(
        self,
        *,
        dependency: str,
        tested_at: datetime,
        success: bool,
        code: str,
    ) -> PortalCredentials:
        normalized_dependency = str(dependency).strip()
        normalized_code = str(code).strip()
        if not normalized_dependency:
            raise ValueError("La dependencia es obligatoria.")
        if not normalized_code:
            raise ValueError("El código del resultado es obligatorio.")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE portal_credentials
                   SET last_tested_at = ?,
                       last_test_success = ?,
                       last_test_code = ?,
                       updated_at = ?
                 WHERE dependency = ? COLLATE NOCASE
                """,
                (
                    _serialize_datetime(tested_at),
                    int(bool(success)),
                    normalized_code,
                    _serialize_datetime(_utc_now()),
                    normalized_dependency,
                ),
            )
            connection.commit()

        if cursor.rowcount != 1:
            raise PortalCredentialsNotConfiguredError(normalized_dependency)

        record = self.find_by_dependency(normalized_dependency)
        if record is None:
            raise PortalCredentialsNotConfiguredError(normalized_dependency)
        return record

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def _to_domain(row: sqlite3.Row) -> PortalCredentials:
        raw_success = row["last_test_success"]
        return PortalCredentials(
            dependency=str(row["dependency"]),
            portal_username=str(row["portal_username"]),
            encrypted_password=str(row["encrypted_password"]),
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
            last_tested_at=_parse_datetime(row["last_tested_at"]),
            last_test_success=(
                None if raw_success is None else bool(raw_success)
            ),
            last_test_code=(
                None
                if row["last_test_code"] is None
                else str(row["last_test_code"])
            ),
        )
