from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from application.ports.batch_repository import BatchRepository
from application.ports.contract_file_validator import ContractFileValidator
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.errors.batch_errors import (
    BatchAlreadyExistsError,
    BatchNotFoundError,
    InvalidBatchSelectionError,
)
from domain.models.contract_batch import BatchContract, ContractBatch


class BatchCreationService:
    """Convierte una validación almacenada en un lote persistente."""

    def __init__(
        self,
        *,
        validations: ContractFileValidator,
        batches: BatchRepository,
    ) -> None:
        self._validations = validations
        self._batches = batches

    def create(
        self,
        *,
        validation_id: str,
        selected_row_numbers: list[int] | tuple[int, ...],
        actor_user_id: int,
        actor_username: str,
        dependency: str,
    ) -> ContractBatch:
        normalized_validation_id = str(validation_id).strip().casefold()
        normalized_dependency = str(dependency).strip()
        normalized_username = str(actor_username).strip()
        selected_rows = tuple(int(row) for row in selected_row_numbers)

        if not selected_rows:
            raise InvalidBatchSelectionError(
                "Seleccione al menos un contrato válido para crear el lote."
            )
        if len(selected_rows) != len(set(selected_rows)):
            raise InvalidBatchSelectionError(
                "La selección contiene filas repetidas."
            )
        if any(row < 2 for row in selected_rows):
            raise InvalidBatchSelectionError(
                "Los números de fila seleccionados no son válidos."
            )

        if self._batches.get_by_validation(
            normalized_validation_id,
            dependency=normalized_dependency,
        ) is not None:
            raise BatchAlreadyExistsError(normalized_validation_id)

        validation = self._validations.get_validation(
            validation_id=normalized_validation_id,
            dependency=normalized_dependency,
        )
        valid_by_row = {
            result.row_number: result
            for result in validation.validation.valid_rows
        }

        rejected_rows = [
            row for row in selected_rows if row not in valid_by_row
        ]
        if rejected_rows:
            formatted = ", ".join(str(row) for row in rejected_rows)
            raise InvalidBatchSelectionError(
                "Solo pueden incluirse filas válidas de la validación. "
                f"Filas rechazadas: {formatted}."
            )

        contracts: list[BatchContract] = []
        for row_number in selected_rows:
            result = valid_by_row[row_number]
            if result.contract is None:
                raise InvalidBatchSelectionError(
                    f"La fila {row_number} no contiene un contrato válido."
                )
            contracts.append(
                BatchContract(
                    item_id=uuid4(),
                    source_row_number=row_number,
                    contract=result.contract,
                    status=BatchContractStatus.PENDING,
                )
            )

        now = datetime.now(UTC)
        batch = ContractBatch(
            batch_id=uuid4(),
            validation_id=normalized_validation_id,
            source_file_name=validation.original_file_name,
            dependency=normalized_dependency,
            created_by_user_id=int(actor_user_id),
            created_by_username=normalized_username,
            status=BatchStatus.READY,
            contracts=tuple(contracts),
            created_at=now,
            updated_at=now,
        )
        return self._batches.create(batch)

    def get(
        self,
        *,
        batch_id,
        dependency: str,
    ) -> ContractBatch:
        batch = self._batches.get_by_id(
            batch_id,
            dependency=dependency,
        )
        if batch is None:
            raise BatchNotFoundError(str(batch_id))
        return batch

    def list(
        self,
        *,
        dependency: str,
        limit: int = 50,
    ) -> tuple[ContractBatch, ...]:
        return self._batches.list_by_dependency(
            dependency,
            limit=limit,
        )
