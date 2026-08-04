from __future__ import annotations

import json
import re
import sqlite3

from collections.abc import Collection, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from application.ports.execution_repository import (
    ExecutionIdentityConflictError,
    ExecutionRepository,
    ExecutionRepositoryError,
)
from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.models import (
    ContractExecution,
    ExecutionErrorInfo,
)

from adapters.persistence.sqlite.models import (
    CREATE_SCHEMA_SQL,
    SCHEMA_VERSION,
    UPSERT_EXECUTION_SQL,
)


class SQLiteExecutionRepository(ExecutionRepository):
    """
    Implementación SQLite del repositorio de ejecuciones.

    Utiliza una conexión corta por operación para evitar mantener una
    conexión global compartida entre solicitudes, hilos o workers.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        timeout_seconds: float = 10.0,
        auto_initialize: bool = True,
    ) -> None:
        self._database_path = Path(database_path)
        self._timeout_seconds = timeout_seconds

        if self._timeout_seconds <= 0:
            raise ValueError(
                "El timeout de SQLite debe ser mayor que cero."
            )

        self._prepare_parent_directory()

        if auto_initialize:
            self.initialize()

    @property
    def database_path(self) -> Path:
        return self._database_path

    def initialize(self) -> None:
        """
        Crea la tabla y los índices requeridos.

        `PRAGMA user_version` deja registrada la versión de esquema
        para futuras migraciones.
        """

        try:
            with self._connection() as connection:
                connection.executescript(
                    CREATE_SCHEMA_SQL
                )
                connection.execute(
                    f"PRAGMA user_version = {SCHEMA_VERSION}"
                )
        except sqlite3.Error as error:
            raise ExecutionRepositoryError(
                "No fue posible inicializar la base de datos "
                f"SQLite '{self._database_path}': {error}"
            ) from error

    def save(
        self,
        execution: ContractExecution,
    ) -> None:
        """
        Guarda el snapshot completo del agregado.

        Antes del UPSERT se verifica que la identidad lógica no esté
        asociada a otro execution_id.
        """

        parameters = self._serialize_execution(
            execution
        )

        try:
            with self._connection() as connection:
                existing = connection.execute(
                    """
                    SELECT execution_id
                    FROM contract_executions
                    WHERE contract_identity = ?
                      AND dependency_identity = ?
                    """,
                    (
                        parameters["contract_identity"],
                        parameters["dependency_identity"],
                    ),
                ).fetchone()

                if (
                    existing is not None
                    and existing["execution_id"]
                    != parameters["execution_id"]
                ):
                    raise ExecutionIdentityConflictError(
                        "Ya existe otra ejecución para el contrato "
                        f"'{execution.contract_number}' en la "
                        f"dependencia '{execution.dependency}'."
                    )

                connection.execute(
                    UPSERT_EXECUTION_SQL,
                    parameters,
                )

        except ExecutionIdentityConflictError:
            raise
        except sqlite3.Error as error:
            raise ExecutionRepositoryError(
                "No fue posible guardar la ejecución "
                f"'{execution.execution_id}': {error}"
            ) from error

    def get_by_id(
        self,
        execution_id: UUID,
    ) -> ContractExecution | None:
        try:
            with self._connection() as connection:
                row = connection.execute(
                    """
                    SELECT *
                    FROM contract_executions
                    WHERE execution_id = ?
                    """,
                    (str(execution_id),),
                ).fetchone()

        except sqlite3.Error as error:
            raise ExecutionRepositoryError(
                "No fue posible consultar la ejecución "
                f"'{execution_id}': {error}"
            ) from error

        return (
            self._deserialize_execution(row)
            if row is not None
            else None
        )

    def get_by_contract(
        self,
        contract_number: str,
        dependency: str,
    ) -> ContractExecution | None:
        contract_identity = (
            self._normalize_contract_identity(
                contract_number
            )
        )
        dependency_identity = (
            self._normalize_dependency_identity(
                dependency
            )
        )

        try:
            with self._connection() as connection:
                row = connection.execute(
                    """
                    SELECT *
                    FROM contract_executions
                    WHERE contract_identity = ?
                      AND dependency_identity = ?
                    """,
                    (
                        contract_identity,
                        dependency_identity,
                    ),
                ).fetchone()

        except sqlite3.Error as error:
            raise ExecutionRepositoryError(
                "No fue posible consultar el contrato "
                f"'{contract_number}': {error}"
            ) from error

        return (
            self._deserialize_execution(row)
            if row is not None
            else None
        )

    def list_by_status(
        self,
        statuses: Collection[ExecutionStatus] | None = None,
    ) -> tuple[ContractExecution, ...]:
        parameters: tuple[str, ...] = ()
        query = """
            SELECT *
            FROM contract_executions
        """

        if statuses is not None:
            status_values = tuple(
                status.value
                for status in statuses
            )

            if not status_values:
                return ()

            placeholders = ", ".join(
                "?"
                for _ in status_values
            )

            query += (
                f" WHERE status IN ({placeholders})"
            )
            parameters = status_values

        query += """
            ORDER BY updated_at ASC, execution_id ASC
        """

        try:
            with self._connection() as connection:
                rows = connection.execute(
                    query,
                    parameters,
                ).fetchall()

        except sqlite3.Error as error:
            raise ExecutionRepositoryError(
                "No fue posible listar las ejecuciones: "
                f"{error}"
            ) from error

        return tuple(
            self._deserialize_execution(row)
            for row in rows
        )

    def _prepare_parent_directory(self) -> None:
        parent = self._database_path.parent

        try:
            parent.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as error:
            raise ExecutionRepositoryError(
                "No fue posible crear el directorio de la "
                f"base de datos '{parent}': {error}"
            ) from error

    @contextmanager
    def _connection(
        self,
    ) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._timeout_seconds,
        )
        connection.row_factory = sqlite3.Row

        try:
            connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            connection.execute(
                "PRAGMA busy_timeout = "
                f"{int(self._timeout_seconds * 1000)}"
            )

            yield connection
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def _serialize_execution(
        self,
        execution: ContractExecution,
    ) -> dict[str, Any]:
        error = execution.last_error

        return {
            "execution_id": str(
                execution.execution_id
            ),
            "contract_number": (
                execution.contract_number
            ),
            "dependency": execution.dependency,
            "contract_identity": (
                self._normalize_contract_identity(
                    execution.contract_number
                )
            ),
            "dependency_identity": (
                self._normalize_dependency_identity(
                    execution.dependency
                )
            ),
            "status": execution.status.value,
            "last_completed_step": (
                execution.last_completed_step.value
            ),
            "current_step": (
                execution.current_step.value
                if execution.current_step is not None
                else None
            ),
            "last_failed_step": (
                execution.last_failed_step.value
                if execution.last_failed_step is not None
                else None
            ),
            "attempt_count": execution.attempt_count,
            "portal_profile": execution.portal_profile,
            "last_error_code": (
                error.code
                if error is not None
                else None
            ),
            "last_error_category": (
                error.category.value
                if error is not None
                else None
            ),
            "last_error_message": (
                error.message
                if error is not None
                else None
            ),
            "last_error_retryable": (
                int(error.retryable)
                if error is not None
                else None
            ),
            "last_error_metadata": (
                self._serialize_metadata(
                    error.metadata
                )
                if error is not None
                else None
            ),
            "created_at": self._serialize_datetime(
                execution.created_at
            ),
            "started_at": self._serialize_datetime(
                execution.started_at
            ),
            "updated_at": self._serialize_datetime(
                execution.updated_at
            ),
            "completed_at": self._serialize_datetime(
                execution.completed_at
            ),
        }

    def _deserialize_execution(
        self,
        row: sqlite3.Row,
    ) -> ContractExecution:
        try:
            error = self._deserialize_error(row)

            return ContractExecution(
                execution_id=UUID(
                    row["execution_id"]
                ),
                contract_number=row[
                    "contract_number"
                ],
                dependency=row["dependency"],
                status=ExecutionStatus(
                    row["status"]
                ),
                last_completed_step=ContractStep(
                    row["last_completed_step"]
                ),
                current_step=(
                    ContractStep(
                        row["current_step"]
                    )
                    if row["current_step"] is not None
                    else None
                ),
                last_failed_step=(
                    ContractStep(
                        row["last_failed_step"]
                    )
                    if row["last_failed_step"] is not None
                    else None
                ),
                attempt_count=int(
                    row["attempt_count"]
                ),
                portal_profile=row[
                    "portal_profile"
                ],
                last_error=error,
                created_at=self._deserialize_datetime(
                    row["created_at"],
                    required=True,
                ),
                started_at=self._deserialize_datetime(
                    row["started_at"]
                ),
                updated_at=self._deserialize_datetime(
                    row["updated_at"],
                    required=True,
                ),
                completed_at=self._deserialize_datetime(
                    row["completed_at"]
                ),
            )

        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise ExecutionRepositoryError(
                "La fila almacenada de la ejecución "
                f"'{row['execution_id']}' es inválida: {error}"
            ) from error

    def _deserialize_error(
        self,
        row: sqlite3.Row,
    ) -> ExecutionErrorInfo | None:
        error_code = row["last_error_code"]

        if error_code is None:
            return None

        metadata_text = (
            row["last_error_metadata"]
            or "{}"
        )
        metadata = json.loads(metadata_text)

        if not isinstance(metadata, dict):
            raise ValueError(
                "Los metadatos del error no son un objeto JSON."
            )

        return ExecutionErrorInfo(
            code=error_code,
            category=ErrorCategory(
                row["last_error_category"]
            ),
            message=row[
                "last_error_message"
            ],
            retryable=bool(
                row["last_error_retryable"]
            ),
            metadata=metadata,
        )

    @staticmethod
    def _normalize_contract_identity(
        contract_number: str,
    ) -> str:
        """
        La identidad del contrato ignora espacios y mayúsculas.
        Conserva guiones, barras y demás caracteres institucionales.
        """

        return re.sub(
            r"\s+",
            "",
            str(contract_number),
        ).casefold()

    @staticmethod
    def _normalize_dependency_identity(
        dependency: str,
    ) -> str:
        return " ".join(
            str(dependency).split()
        ).casefold()

    @staticmethod
    def _serialize_metadata(
        metadata: dict[str, Any],
    ) -> str:
        return json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

    @staticmethod
    def _serialize_datetime(
        value: datetime | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value

        if normalized.tzinfo is None:
            normalized = normalized.replace(
                tzinfo=timezone.utc
            )

        return normalized.astimezone(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _deserialize_datetime(
        value: str | None,
        *,
        required: bool = False,
    ) -> datetime | None:
        if value is None:
            if required:
                raise ValueError(
                    "Falta una fecha obligatoria."
                )

            return None

        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )
        return parsed