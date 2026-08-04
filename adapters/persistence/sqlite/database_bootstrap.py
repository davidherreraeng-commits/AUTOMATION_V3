from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


SCHEMA_VERSION = 1
BASELINE_MIGRATION_ID = "001_runtime_schema_baseline"


class SQLiteDatabaseBootstrapError(RuntimeError):
    """Error base al preparar la base de datos operativa."""


class SQLiteDatabaseIntegrityError(SQLiteDatabaseBootstrapError):
    """La base SQLite existente no supera la comprobación de integridad."""


class SQLiteSchemaVerificationError(SQLiteDatabaseBootstrapError):
    """El esquema resultante no contiene las estructuras obligatorias."""


@dataclass(frozen=True, slots=True)
class SQLiteBootstrapReport:
    database_path: Path
    schema_version: int
    created_database: bool
    migration_applied: bool
    applied_migrations: tuple[str, ...]
    backup_path: Path | None
    tables: tuple[str, ...]


_REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "users": frozenset(
        {
            "id",
            "username",
            "password_hash",
            "dependency",
            "role",
            "is_active",
            "must_change_password",
            "created_at",
            "updated_at",
            "last_login_at",
        }
    ),
    "portal_credentials": frozenset(
        {
            "dependency",
            "portal_username",
            "encrypted_password",
            "created_at",
            "updated_at",
            "last_tested_at",
            "last_test_success",
            "last_test_code",
        }
    ),
    "contract_batches": frozenset(
        {
            "batch_id",
            "validation_id",
            "source_file_name",
            "dependency",
            "dependency_identity",
            "created_by_user_id",
            "created_by_username",
            "status",
            "selected_count",
            "created_at",
            "updated_at",
        }
    ),
    "batch_contracts": frozenset(
        {
            "item_id",
            "batch_id",
            "source_row_number",
            "contract_number",
            "contract_identity",
            "dependency",
            "contractor_document",
            "status",
            "last_message",
            "contract_payload",
            "created_at",
            "updated_at",
        }
    ),
    "contract_executions": frozenset(
        {
            "execution_id",
            "contract_number",
            "dependency",
            "contract_identity",
            "dependency_identity",
            "status",
            "last_completed_step",
            "current_step",
            "last_failed_step",
            "attempt_count",
            "created_at",
            "updated_at",
        }
    ),
    "real_write_authorizations": frozenset(
        {
            "authorization_id",
            "token_hash",
            "status",
            "actor_user_id",
            "actor_username",
            "dependency",
            "batch_id",
            "item_id",
            "contract_number",
            "issued_at",
            "expires_at",
        }
    ),
    "real_write_authorization_events": frozenset(
        {
            "event_id",
            "authorization_id",
            "event_type",
            "recorded_at",
        }
    ),
    "rpa_schema_migrations": frozenset(
        {
            "migration_id",
            "schema_version",
            "description",
            "applied_at",
        }
    ),
}

_MIGRATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS rpa_schema_migrations (
    migration_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL CHECK (schema_version > 0),
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
"""


class SQLiteDatabaseBootstrapper:
    """
    Inicializa y verifica la base operativa sin reemplazar datos existentes.

    Los inicializadores recibidos deben ser idempotentes. Antes de aplicar la
    migración base a una base existente se crea una copia coherente mediante
    la API de respaldo de SQLite.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        backup_directory: str | Path | None = None,
        backup_before_migration: bool = True,
    ) -> None:
        self._database_path = Path(database_path).expanduser().resolve()
        self._backup_directory = (
            Path(backup_directory).expanduser().resolve()
            if backup_directory is not None
            else self._database_path.parent / "database_backups"
        )
        self._backup_before_migration = bool(backup_before_migration)

    @property
    def database_path(self) -> Path:
        return self._database_path

    @property
    def backup_directory(self) -> Path:
        return self._backup_directory

    def initialize(
        self,
        initializers: Iterable[Callable[[], None]],
    ) -> SQLiteBootstrapReport:
        existed_before = self._database_path.is_file()
        had_content_before = (
            existed_before and self._database_path.stat().st_size > 0
        )

        self._database_path.parent.mkdir(parents=True, exist_ok=True)

        if had_content_before:
            self._assert_integrity()

        migration_pending = not self._migration_is_applied(
            BASELINE_MIGRATION_ID
        )
        backup_path: Path | None = None

        if (
            migration_pending
            and had_content_before
            and self._backup_before_migration
        ):
            backup_path = self._create_backup()

        try:
            for initializer in initializers:
                initializer()

            applied_migrations: list[str] = []
            with self._connect() as connection:
                connection.executescript(_MIGRATION_SCHEMA)
                if migration_pending:
                    connection.execute(
                        """
                        INSERT INTO rpa_schema_migrations (
                            migration_id,
                            schema_version,
                            description,
                            applied_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            BASELINE_MIGRATION_ID,
                            SCHEMA_VERSION,
                            (
                                "Esquema operativo consolidado para usuarios, "
                                "credenciales, lotes, ejecuciones y "
                                "autorizaciones temporales."
                            ),
                            datetime.now(UTC).isoformat(),
                        ),
                    )
                    applied_migrations.append(BASELINE_MIGRATION_ID)

                connection.execute(
                    f"PRAGMA user_version = {SCHEMA_VERSION}"
                )
                connection.commit()

            tables = self._verify_schema()
        except SQLiteDatabaseBootstrapError:
            raise
        except Exception as error:
            raise SQLiteDatabaseBootstrapError(
                "No fue posible inicializar la base de datos operativa "
                f"'{self._database_path}': {error}"
            ) from error

        return SQLiteBootstrapReport(
            database_path=self._database_path,
            schema_version=SCHEMA_VERSION,
            created_database=not existed_before,
            migration_applied=bool(applied_migrations),
            applied_migrations=tuple(applied_migrations),
            backup_path=backup_path,
            tables=tables,
        )

    def _migration_is_applied(self, migration_id: str) -> bool:
        if not self._database_path.is_file():
            return False

        try:
            with self._connect() as connection:
                exists = connection.execute(
                    """
                    SELECT 1
                      FROM sqlite_master
                     WHERE type = 'table'
                       AND name = 'rpa_schema_migrations'
                    """
                ).fetchone()
                if exists is None:
                    return False

                row = connection.execute(
                    """
                    SELECT 1
                      FROM rpa_schema_migrations
                     WHERE migration_id = ?
                    """,
                    (migration_id,),
                ).fetchone()
                return row is not None
        except sqlite3.Error as error:
            raise SQLiteDatabaseBootstrapError(
                "No fue posible consultar el historial de migraciones: "
                f"{error}"
            ) from error

    def _assert_integrity(self) -> None:
        try:
            with self._connect(read_only=True) as connection:
                rows = connection.execute("PRAGMA quick_check").fetchall()
        except sqlite3.Error as error:
            raise SQLiteDatabaseIntegrityError(
                "No fue posible abrir la base SQLite existente para "
                f"comprobar su integridad: {error}"
            ) from error

        messages = tuple(str(row[0]) for row in rows)
        if messages != ("ok",):
            raise SQLiteDatabaseIntegrityError(
                "La base SQLite existente no supera PRAGMA quick_check: "
                + "; ".join(messages)
            )

    def _create_backup(self) -> Path:
        self._backup_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        backup_path = self._backup_directory / (
            f"{self._database_path.stem}_before_6C14G_{timestamp}.sqlite3"
        )

        try:
            with self._connect(read_only=True) as source:
                with sqlite3.connect(backup_path) as destination:
                    source.backup(destination)
                    destination.commit()
        except sqlite3.Error as error:
            backup_path.unlink(missing_ok=True)
            raise SQLiteDatabaseBootstrapError(
                "No fue posible crear el respaldo previo a la migración: "
                f"{error}"
            ) from error

        return backup_path

    def _verify_schema(self) -> tuple[str, ...]:
        try:
            with self._connect() as connection:
                quick_check = tuple(
                    str(row[0])
                    for row in connection.execute(
                        "PRAGMA quick_check"
                    ).fetchall()
                )
                if quick_check != ("ok",):
                    raise SQLiteDatabaseIntegrityError(
                        "La base resultante no supera PRAGMA quick_check: "
                        + "; ".join(quick_check)
                    )

                foreign_key_errors = connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()
                if foreign_key_errors:
                    raise SQLiteSchemaVerificationError(
                        "La base resultante contiene referencias foráneas "
                        "inválidas."
                    )

                table_rows = connection.execute(
                    """
                    SELECT name
                      FROM sqlite_master
                     WHERE type = 'table'
                       AND name NOT LIKE 'sqlite_%'
                     ORDER BY name
                    """
                ).fetchall()
                tables = tuple(str(row[0]) for row in table_rows)
                table_set = set(tables)

                missing_tables = sorted(
                    set(_REQUIRED_COLUMNS) - table_set
                )
                if missing_tables:
                    raise SQLiteSchemaVerificationError(
                        "Faltan tablas obligatorias: "
                        + ", ".join(missing_tables)
                    )

                for table_name, required_columns in (
                    _REQUIRED_COLUMNS.items()
                ):
                    columns = {
                        str(row[1])
                        for row in connection.execute(
                            f'PRAGMA table_info("{table_name}")'
                        ).fetchall()
                    }
                    missing_columns = sorted(
                        required_columns - columns
                    )
                    if missing_columns:
                        raise SQLiteSchemaVerificationError(
                            f"La tabla '{table_name}' no contiene: "
                            + ", ".join(missing_columns)
                        )

                migration = connection.execute(
                    """
                    SELECT schema_version
                      FROM rpa_schema_migrations
                     WHERE migration_id = ?
                    """,
                    (BASELINE_MIGRATION_ID,),
                ).fetchone()
                if migration is None or int(migration[0]) != SCHEMA_VERSION:
                    raise SQLiteSchemaVerificationError(
                        "La migración base no quedó registrada."
                    )

                connection.execute("PRAGMA optimize")
                return tables
        except SQLiteDatabaseBootstrapError:
            raise
        except sqlite3.Error as error:
            raise SQLiteSchemaVerificationError(
                "No fue posible verificar el esquema SQLite: "
                f"{error}"
            ) from error

    def _connect(self, *, read_only: bool = False) -> sqlite3.Connection:
        if read_only:
            uri = self._database_path.as_uri() + "?mode=ro"
            connection = sqlite3.connect(uri, uri=True, timeout=30.0)
        else:
            connection = sqlite3.connect(
                self._database_path,
                timeout=30.0,
            )

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection
