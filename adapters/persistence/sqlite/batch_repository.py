from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID

from application.ports.batch_repository import BatchRepository
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.enums.contractor_nature import ContractorNature
from domain.errors.batch_errors import (
    BatchAlreadyExistsError,
    BatchNotFoundError,
    BatchRepositoryError,
)
from domain.errors.batch_execution_errors import (
    BatchExecutionInProgressError,
    BatchExecutionStateError,
    BatchNotReadyForExecutionError,
)
from domain.models.budget import BudgetData
from domain.models.contract import ContractData
from domain.models.contract_batch import BatchContract, ContractBatch
from domain.models.contractor import ContractorData
from domain.models.supervisor import SupervisorData


_SCHEMA = """
CREATE TABLE IF NOT EXISTS contract_batches (
    batch_id TEXT PRIMARY KEY,
    validation_id TEXT NOT NULL,
    source_file_name TEXT NOT NULL,
    dependency TEXT NOT NULL,
    dependency_identity TEXT NOT NULL,
    created_by_user_id INTEGER NOT NULL CHECK (created_by_user_id > 0),
    created_by_username TEXT NOT NULL,
    status TEXT NOT NULL,
    selected_count INTEGER NOT NULL CHECK (selected_count > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CONSTRAINT uq_batch_validation_dependency
        UNIQUE (validation_id, dependency_identity)
);

CREATE TABLE IF NOT EXISTS batch_contracts (
    item_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    source_row_number INTEGER NOT NULL CHECK (source_row_number >= 2),
    contract_number TEXT NOT NULL,
    contract_identity TEXT NOT NULL,
    dependency TEXT NOT NULL,
    contractor_document TEXT NOT NULL,
    status TEXT NOT NULL,
    last_message TEXT NULL,
    contract_payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (batch_id)
        REFERENCES contract_batches(batch_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_batch_source_row
        UNIQUE (batch_id, source_row_number),
    CONSTRAINT uq_batch_contract_identity
        UNIQUE (batch_id, contract_identity)
);

CREATE INDEX IF NOT EXISTS idx_contract_batches_dependency_created
    ON contract_batches(dependency_identity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contract_batches_status
    ON contract_batches(status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_processing_batch_per_dependency
    ON contract_batches(dependency_identity)
    WHERE status = 'PROCESSING';
CREATE INDEX IF NOT EXISTS idx_batch_contracts_batch
    ON batch_contracts(batch_id, source_row_number);
"""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _datetime_to_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _datetime_from_text(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _date_to_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _date_from_text(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _identity(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _contract_to_payload(contract: ContractData) -> str:
    payload = {
        "contract_number": contract.contract_number,
        "dependency": contract.dependency,
        "contractor": {
            "document_number": contract.contractor.document_number,
            "nature": contract.contractor.nature.value,
        },
        "project_code": contract.project_code,
        "object_description": contract.object_description,
        "signing_date": contract.signing_date.isoformat(),
        "starting_date": contract.starting_date.isoformat(),
        "amount": format(contract.amount, "f"),
        "term_days": contract.term_days,
        "process_type": contract.process_type,
        "procedure": contract.procedure,
        "contract_type": contract.contract_type,
        "budget": {
            "year": contract.budget.year,
            "item": contract.budget.item,
            "subsector": contract.budget.subsector,
            "cdp_code": contract.budget.cdp_code,
            "gross_total": format(contract.budget.gross_total, "f"),
            "budget_register_number": contract.budget.budget_register_number,
            "budget_register_date": _date_to_text(
                contract.budget.budget_register_date
            ),
        },
        "supervisor": {
            "document_number": contract.supervisor.document_number,
            "supervisor_type": contract.supervisor.supervisor_type,
        },
        "secop_url": contract.secop_url,
        "guarantee_approval_date": _date_to_text(
            contract.guarantee_approval_date
        ),
        "website_publication_date": _date_to_text(
            contract.website_publication_date
        ),
        "secop_publication_date": _date_to_text(
            contract.secop_publication_date
        ),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _contract_from_payload(raw_payload: str) -> ContractData:
    payload: dict[str, Any] = json.loads(raw_payload)
    contractor_payload = payload["contractor"]
    budget_payload = payload["budget"]
    supervisor_payload = payload["supervisor"]

    return ContractData(
        contract_number=payload["contract_number"],
        dependency=payload["dependency"],
        contractor=ContractorData(
            document_number=contractor_payload["document_number"],
            nature=ContractorNature(contractor_payload["nature"]),
        ),
        project_code=payload["project_code"],
        object_description=payload["object_description"],
        signing_date=date.fromisoformat(payload["signing_date"]),
        starting_date=date.fromisoformat(payload["starting_date"]),
        amount=Decimal(payload["amount"]),
        term_days=int(payload["term_days"]),
        process_type=payload["process_type"],
        procedure=payload["procedure"],
        contract_type=payload["contract_type"],
        budget=BudgetData(
            year=int(budget_payload["year"]),
            item=budget_payload["item"],
            subsector=budget_payload["subsector"],
            cdp_code=budget_payload["cdp_code"],
            gross_total=Decimal(budget_payload["gross_total"]),
            budget_register_number=budget_payload.get(
                "budget_register_number"
            ),
            budget_register_date=_date_from_text(
                budget_payload.get("budget_register_date")
            ),
        ),
        supervisor=SupervisorData(
            document_number=supervisor_payload["document_number"],
            supervisor_type=supervisor_payload.get("supervisor_type"),
        ),
        secop_url=payload.get("secop_url"),
        guarantee_approval_date=_date_from_text(
            payload.get("guarantee_approval_date")
        ),
        website_publication_date=_date_from_text(
            payload.get("website_publication_date")
        ),
        secop_publication_date=_date_from_text(
            payload.get("secop_publication_date")
        ),
    )


class SQLiteBatchRepository(BatchRepository):
    """Persistencia transaccional de lotes y snapshots contractuales."""

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
                columns = {
                    str(row[1])
                    for row in connection.execute(
                        "PRAGMA table_info(batch_contracts)"
                    ).fetchall()
                }
                if "last_message" not in columns:
                    connection.execute(
                        "ALTER TABLE batch_contracts "
                        "ADD COLUMN last_message TEXT NULL"
                    )
                connection.commit()
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible inicializar los lotes: {error}"
            ) from error

    def create(self, batch: ContractBatch) -> ContractBatch:
        now_text = _datetime_to_text(batch.created_at)
        dependency_identity = _identity(batch.dependency)

        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO contract_batches (
                        batch_id,
                        validation_id,
                        source_file_name,
                        dependency,
                        dependency_identity,
                        created_by_user_id,
                        created_by_username,
                        status,
                        selected_count,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(batch.batch_id),
                        batch.validation_id,
                        batch.source_file_name,
                        batch.dependency,
                        dependency_identity,
                        batch.created_by_user_id,
                        batch.created_by_username,
                        batch.status.value,
                        batch.selected_count,
                        now_text,
                        _datetime_to_text(batch.updated_at),
                    ),
                )

                for item in batch.contracts:
                    connection.execute(
                        """
                        INSERT INTO batch_contracts (
                            item_id,
                            batch_id,
                            source_row_number,
                            contract_number,
                            contract_identity,
                            dependency,
                            contractor_document,
                            status,
                            last_message,
                            contract_payload,
                            created_at,
                            updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(item.item_id),
                            str(batch.batch_id),
                            item.source_row_number,
                            item.contract.contract_number,
                            _identity(item.contract.contract_number),
                            item.contract.dependency,
                            item.contract.contractor.document_number,
                            item.status.value,
                            item.last_message,
                            _contract_to_payload(item.contract),
                            now_text,
                            now_text,
                        ),
                    )
                connection.commit()
        except sqlite3.IntegrityError as error:
            if (
                "contract_batches.validation_id" in str(error)
                or "uq_batch_validation_dependency" in str(error)
                or "UNIQUE constraint failed: contract_batches.validation_id" in str(error)
            ):
                raise BatchAlreadyExistsError(batch.validation_id) from error
            raise BatchRepositoryError(
                f"No fue posible persistir el lote: {error}"
            ) from error
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible persistir el lote: {error}"
            ) from error

        stored = self.get_by_id(batch.batch_id, dependency=batch.dependency)
        if stored is None:
            raise BatchRepositoryError("No fue posible recuperar el lote creado.")
        return stored

    def get_by_id(
        self,
        batch_id: UUID,
        *,
        dependency: str,
    ) -> ContractBatch | None:
        try:
            with self._connect() as connection:
                batch_row = connection.execute(
                    """
                    SELECT *
                      FROM contract_batches
                     WHERE batch_id = ?
                       AND dependency_identity = ?
                    """,
                    (str(batch_id), _identity(dependency)),
                ).fetchone()
                if batch_row is None:
                    return None
                item_rows = connection.execute(
                    """
                    SELECT *
                      FROM batch_contracts
                     WHERE batch_id = ?
                     ORDER BY source_row_number ASC
                    """,
                    (str(batch_id),),
                ).fetchall()
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible consultar el lote: {error}"
            ) from error

        return self._to_domain(batch_row, item_rows)

    def get_by_validation(
        self,
        validation_id: str,
        *,
        dependency: str,
    ) -> ContractBatch | None:
        try:
            with self._connect() as connection:
                batch_row = connection.execute(
                    """
                    SELECT *
                      FROM contract_batches
                     WHERE validation_id = ?
                       AND dependency_identity = ?
                    """,
                    (str(validation_id).strip().casefold(), _identity(dependency)),
                ).fetchone()
                if batch_row is None:
                    return None
                item_rows = connection.execute(
                    """
                    SELECT *
                      FROM batch_contracts
                     WHERE batch_id = ?
                     ORDER BY source_row_number ASC
                    """,
                    (batch_row["batch_id"],),
                ).fetchall()
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible consultar la validación del lote: {error}"
            ) from error

        return self._to_domain(batch_row, item_rows)

    def list_by_dependency(
        self,
        dependency: str,
        *,
        limit: int = 50,
    ) -> tuple[ContractBatch, ...]:
        safe_limit = max(1, min(int(limit), 200))
        try:
            with self._connect() as connection:
                batch_rows = connection.execute(
                    """
                    SELECT *
                      FROM contract_batches
                     WHERE dependency_identity = ?
                     ORDER BY created_at DESC
                     LIMIT ?
                    """,
                    (_identity(dependency), safe_limit),
                ).fetchall()
                batches: list[ContractBatch] = []
                for batch_row in batch_rows:
                    item_rows = connection.execute(
                        """
                        SELECT *
                          FROM batch_contracts
                         WHERE batch_id = ?
                         ORDER BY source_row_number ASC
                        """,
                        (batch_row["batch_id"],),
                    ).fetchall()
                    batches.append(self._to_domain(batch_row, item_rows))
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible listar los lotes: {error}"
            ) from error
        return tuple(batches)

    def get_processing_by_dependency(
        self,
        dependency: str,
    ) -> ContractBatch | None:
        try:
            with self._connect() as connection:
                batch_row = connection.execute(
                    """
                    SELECT *
                      FROM contract_batches
                     WHERE dependency_identity = ?
                       AND status = ?
                     ORDER BY updated_at ASC
                     LIMIT 1
                    """,
                    (_identity(dependency), BatchStatus.PROCESSING.value),
                ).fetchone()
                if batch_row is None:
                    return None
                item_rows = connection.execute(
                    """
                    SELECT *
                      FROM batch_contracts
                     WHERE batch_id = ?
                     ORDER BY source_row_number ASC
                    """,
                    (batch_row["batch_id"],),
                ).fetchall()
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible consultar el lote activo: {error}"
            ) from error
        return self._to_domain(batch_row, item_rows)

    def claim_for_processing(
        self,
        batch_id: UUID,
        *,
        dependency: str,
    ) -> ContractBatch:
        now_text = _datetime_to_text(_utc_now())
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT status
                      FROM contract_batches
                     WHERE batch_id = ?
                       AND dependency_identity = ?
                    """,
                    (str(batch_id), _identity(dependency)),
                ).fetchone()
                if row is None:
                    raise BatchNotFoundError(str(batch_id))

                current_status = BatchStatus(str(row["status"]))
                if current_status is not BatchStatus.READY:
                    raise BatchNotReadyForExecutionError(current_status.value)

                active = connection.execute(
                    """
                    SELECT batch_id
                      FROM contract_batches
                     WHERE dependency_identity = ?
                       AND status = ?
                       AND batch_id <> ?
                     LIMIT 1
                    """,
                    (
                        _identity(dependency),
                        BatchStatus.PROCESSING.value,
                        str(batch_id),
                    ),
                ).fetchone()
                if active is not None:
                    raise BatchExecutionInProgressError(dependency)

                cursor = connection.execute(
                    """
                    UPDATE contract_batches
                       SET status = ?, updated_at = ?
                     WHERE batch_id = ?
                       AND dependency_identity = ?
                       AND status = ?
                    """,
                    (
                        BatchStatus.PROCESSING.value,
                        now_text,
                        str(batch_id),
                        _identity(dependency),
                        BatchStatus.READY.value,
                    ),
                )
                if cursor.rowcount != 1:
                    raise BatchExecutionStateError(
                        "No fue posible reservar el lote para ejecución."
                    )
                connection.commit()
        except sqlite3.IntegrityError as error:
            if "uq_processing_batch_per_dependency" in str(error) or (
                "UNIQUE constraint failed: contract_batches.dependency_identity"
                in str(error)
            ):
                raise BatchExecutionInProgressError(dependency) from error
            raise BatchRepositoryError(
                f"No fue posible reservar el lote: {error}"
            ) from error
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible reservar el lote: {error}"
            ) from error

        stored = self.get_by_id(batch_id, dependency=dependency)
        if stored is None:
            raise BatchNotFoundError(str(batch_id))
        return stored

    def update_contract_status(
        self,
        batch_id: UUID,
        item_id: UUID,
        *,
        dependency: str,
        status: BatchContractStatus,
        message: str | None = None,
    ) -> ContractBatch:
        if not isinstance(status, BatchContractStatus):
            raise TypeError("El estado del contrato del lote no es válido.")

        normalized_message = None
        if message is not None:
            normalized_message = str(message).strip() or None

        allowed_transitions = {
            BatchContractStatus.PENDING: {BatchContractStatus.PROCESSING},
            BatchContractStatus.PROCESSING: {
                BatchContractStatus.COMPLETED,
                BatchContractStatus.FAILED,
                BatchContractStatus.MANUAL_REVIEW,
            },
        }
        now_text = _datetime_to_text(_utc_now())

        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                batch_row = connection.execute(
                    """
                    SELECT status
                      FROM contract_batches
                     WHERE batch_id = ?
                       AND dependency_identity = ?
                    """,
                    (str(batch_id), _identity(dependency)),
                ).fetchone()
                if batch_row is None:
                    raise BatchNotFoundError(str(batch_id))
                if BatchStatus(str(batch_row["status"])) is not BatchStatus.PROCESSING:
                    raise BatchExecutionStateError(
                        "Solo puede actualizarse un contrato de un lote PROCESSING."
                    )

                item_row = connection.execute(
                    """
                    SELECT status
                      FROM batch_contracts
                     WHERE item_id = ? AND batch_id = ?
                    """,
                    (str(item_id), str(batch_id)),
                ).fetchone()
                if item_row is None:
                    raise BatchExecutionStateError(
                        "El contrato no pertenece al lote indicado."
                    )

                current = BatchContractStatus(str(item_row["status"]))
                if current is not status and status not in allowed_transitions.get(
                    current, set()
                ):
                    raise BatchExecutionStateError(
                        "Transición de contrato inválida: "
                        f"{current.value} -> {status.value}."
                    )

                connection.execute(
                    """
                    UPDATE batch_contracts
                       SET status = ?, last_message = ?, updated_at = ?
                     WHERE item_id = ? AND batch_id = ?
                    """,
                    (
                        status.value,
                        normalized_message,
                        now_text,
                        str(item_id),
                        str(batch_id),
                    ),
                )
                connection.execute(
                    """
                    UPDATE contract_batches
                       SET updated_at = ?
                     WHERE batch_id = ?
                    """,
                    (now_text, str(batch_id)),
                )
                connection.commit()
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible actualizar el contrato del lote: {error}"
            ) from error

        stored = self.get_by_id(batch_id, dependency=dependency)
        if stored is None:
            raise BatchNotFoundError(str(batch_id))
        return stored

    def finish_processing(
        self,
        batch_id: UUID,
        *,
        dependency: str,
        status: BatchStatus,
    ) -> ContractBatch:
        allowed = {
            BatchStatus.COMPLETED,
            BatchStatus.COMPLETED_WITH_ERRORS,
            BatchStatus.FAILED,
        }
        if status not in allowed:
            raise BatchExecutionStateError(
                f"El estado final del lote no es válido: {status.value}."
            )

        now_text = _datetime_to_text(_utc_now())
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    UPDATE contract_batches
                       SET status = ?, updated_at = ?
                     WHERE batch_id = ?
                       AND dependency_identity = ?
                       AND status = ?
                    """,
                    (
                        status.value,
                        now_text,
                        str(batch_id),
                        _identity(dependency),
                        BatchStatus.PROCESSING.value,
                    ),
                )
                if cursor.rowcount != 1:
                    existing = connection.execute(
                        """
                        SELECT status
                          FROM contract_batches
                         WHERE batch_id = ?
                           AND dependency_identity = ?
                        """,
                        (str(batch_id), _identity(dependency)),
                    ).fetchone()
                    if existing is None:
                        raise BatchNotFoundError(str(batch_id))
                    raise BatchExecutionStateError(
                        "El lote no se encuentra en PROCESSING. "
                        f"Estado actual: {existing['status']}."
                    )
                connection.commit()
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible finalizar el lote: {error}"
            ) from error

        stored = self.get_by_id(batch_id, dependency=dependency)
        if stored is None:
            raise BatchNotFoundError(str(batch_id))
        return stored

    def cancel_ready(
        self,
        batch_id: UUID,
        *,
        dependency: str,
    ) -> ContractBatch:
        now_text = _datetime_to_text(_utc_now())
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    UPDATE contract_batches
                       SET status = ?, updated_at = ?
                     WHERE batch_id = ?
                       AND dependency_identity = ?
                       AND status = ?
                    """,
                    (
                        BatchStatus.CANCELLED.value,
                        now_text,
                        str(batch_id),
                        _identity(dependency),
                        BatchStatus.READY.value,
                    ),
                )
                if cursor.rowcount != 1:
                    existing = connection.execute(
                        """
                        SELECT status
                          FROM contract_batches
                         WHERE batch_id = ?
                           AND dependency_identity = ?
                        """,
                        (str(batch_id), _identity(dependency)),
                    ).fetchone()
                    if existing is None:
                        raise BatchNotFoundError(str(batch_id))
                    raise BatchExecutionStateError(
                        "Solo puede cancelarse un lote en estado READY. "
                        f"Estado actual: {existing['status']}."
                    )
                connection.commit()
        except sqlite3.Error as error:
            raise BatchRepositoryError(
                f"No fue posible cancelar el lote: {error}"
            ) from error

        stored = self.get_by_id(batch_id, dependency=dependency)
        if stored is None:
            raise BatchNotFoundError(str(batch_id))
        return stored

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def _to_domain(
        batch_row: sqlite3.Row,
        item_rows: list[sqlite3.Row],
    ) -> ContractBatch:
        items = tuple(
            BatchContract(
                item_id=UUID(str(row["item_id"])),
                source_row_number=int(row["source_row_number"]),
                contract=_contract_from_payload(str(row["contract_payload"])),
                status=BatchContractStatus(str(row["status"])),
                last_message=(
                    None
                    if row["last_message"] is None
                    else str(row["last_message"])
                ),
            )
            for row in item_rows
        )
        if int(batch_row["selected_count"]) != len(items):
            raise BatchRepositoryError(
                "El número de contratos del lote no coincide con su cabecera."
            )

        return ContractBatch(
            batch_id=UUID(str(batch_row["batch_id"])),
            validation_id=str(batch_row["validation_id"]),
            source_file_name=str(batch_row["source_file_name"]),
            dependency=str(batch_row["dependency"]),
            created_by_user_id=int(batch_row["created_by_user_id"]),
            created_by_username=str(batch_row["created_by_username"]),
            status=BatchStatus(str(batch_row["status"])),
            contracts=items,
            created_at=_datetime_from_text(str(batch_row["created_at"])),
            updated_at=_datetime_from_text(str(batch_row["updated_at"])),
        )
