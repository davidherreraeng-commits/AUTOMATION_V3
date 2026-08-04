from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from domain.enums.user_role import UserRole
from domain.errors.user_errors import (
    UserAlreadyExistsError,
    UserNotFoundError,
)
from domain.models.user_account import UserAccount


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    dependency TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('OPERATOR', 'SUPERUSER')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    must_change_password INTEGER NOT NULL DEFAULT 0
        CHECK (must_change_password IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_dependency
    ON users(dependency);
CREATE INDEX IF NOT EXISTS idx_users_active
    ON users(is_active);
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


class SQLiteUserRepository:
    """Persistencia SQLite para cuentas de usuario."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path).expanduser().resolve()

    @property
    def database_path(self) -> Path:
        return self._database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)
            connection.commit()

    def find_by_id(self, user_id: int) -> UserAccount | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (int(user_id),),
            ).fetchone()
        return self._to_domain(row) if row else None

    def find_by_username(self, username: str) -> UserAccount | None:
        normalized = str(username).strip()
        if not normalized:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
                (normalized,),
            ).fetchone()
        return self._to_domain(row) if row else None

    def list_by_dependency(self, dependency: str) -> list[UserAccount]:
        normalized = str(dependency).strip()
        if not normalized:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                  FROM users
                 WHERE dependency = ? COLLATE NOCASE
                 ORDER BY username COLLATE NOCASE ASC
                """,
                (normalized,),
            ).fetchall()

        return [self._to_domain(row) for row in rows]

    def create(
        self,
        *,
        username: str,
        password_hash: str,
        dependency: str,
        role: UserRole,
        is_active: bool = True,
        must_change_password: bool = False,
    ) -> UserAccount:
        normalized_username = str(username).strip()
        normalized_dependency = str(dependency).strip()
        normalized_hash = str(password_hash).strip()

        if not normalized_username:
            raise ValueError("El nombre de usuario es obligatorio.")
        if not normalized_dependency:
            raise ValueError("La dependencia es obligatoria.")
        if not normalized_hash:
            raise ValueError("El hash de contraseña es obligatorio.")

        now = _utc_now()

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (
                        username,
                        password_hash,
                        dependency,
                        role,
                        is_active,
                        must_change_password,
                        created_at,
                        updated_at,
                        last_login_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        normalized_username,
                        normalized_hash,
                        normalized_dependency,
                        role.value,
                        int(bool(is_active)),
                        int(bool(must_change_password)),
                        _serialize_datetime(now),
                        _serialize_datetime(now),
                    ),
                )
                connection.commit()
                user_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            if "users.username" in str(error):
                raise UserAlreadyExistsError(normalized_username) from error
            raise

        user = self.find_by_id(user_id)
        if user is None:
            raise RuntimeError("No fue posible recuperar el usuario creado.")
        return user

    def update_password(
        self,
        *,
        user_id: int,
        password_hash: str,
        must_change_password: bool = False,
    ) -> UserAccount:
        normalized_hash = str(password_hash).strip()
        if not normalized_hash:
            raise ValueError("El hash de contraseña es obligatorio.")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE users
                   SET password_hash = ?,
                       must_change_password = ?,
                       updated_at = ?
                 WHERE id = ?
                """,
                (
                    normalized_hash,
                    int(bool(must_change_password)),
                    _serialize_datetime(_utc_now()),
                    int(user_id),
                ),
            )
            connection.commit()

        if cursor.rowcount != 1:
            raise UserNotFoundError(int(user_id))

        return self._require_user(int(user_id))

    def set_active(
        self,
        *,
        user_id: int,
        is_active: bool,
    ) -> UserAccount:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE users
                   SET is_active = ?,
                       updated_at = ?
                 WHERE id = ?
                """,
                (
                    int(bool(is_active)),
                    _serialize_datetime(_utc_now()),
                    int(user_id),
                ),
            )
            connection.commit()

        if cursor.rowcount != 1:
            raise UserNotFoundError(int(user_id))

        return self._require_user(int(user_id))

    def record_successful_login(
        self,
        *,
        user_id: int,
        occurred_at: datetime,
    ) -> UserAccount:
        normalized_occurred_at = occurred_at
        if normalized_occurred_at.tzinfo is None:
            normalized_occurred_at = normalized_occurred_at.replace(
                tzinfo=timezone.utc
            )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE users
                   SET last_login_at = ?,
                       updated_at = ?
                 WHERE id = ?
                """,
                (
                    _serialize_datetime(normalized_occurred_at),
                    _serialize_datetime(_utc_now()),
                    int(user_id),
                ),
            )
            connection.commit()

        if cursor.rowcount != 1:
            raise UserNotFoundError(int(user_id))

        return self._require_user(int(user_id))

    def _require_user(self, user_id: int) -> UserAccount:
        user = self.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

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
    def _to_domain(row: sqlite3.Row) -> UserAccount:
        return UserAccount(
            user_id=int(row["id"]),
            username=str(row["username"]),
            password_hash=str(row["password_hash"]),
            dependency=str(row["dependency"]),
            role=UserRole(str(row["role"])),
            is_active=bool(row["is_active"]),
            must_change_password=bool(row["must_change_password"]),
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
            last_login_at=_parse_datetime(row["last_login_at"]),
        )
