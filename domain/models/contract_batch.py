from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.models.contract import ContractData


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class BatchContract:
    """Snapshot inmutable de un contrato seleccionado para un lote."""

    item_id: UUID
    source_row_number: int
    contract: ContractData
    status: BatchContractStatus = BatchContractStatus.PENDING
    last_message: str | None = None

    def __post_init__(self) -> None:
        if self.source_row_number < 2:
            raise ValueError("La fila de origen debe ser igual o superior a 2.")
        if not isinstance(self.status, BatchContractStatus):
            raise TypeError("El estado del contrato del lote no es válido.")
        if self.last_message is not None:
            normalized_message = str(self.last_message).strip() or None
            object.__setattr__(self, "last_message", normalized_message)


@dataclass(frozen=True, slots=True)
class ContractBatch:
    """Lote persistido y listo para una ejecución posterior."""

    batch_id: UUID
    validation_id: str
    source_file_name: str
    dependency: str
    created_by_user_id: int
    created_by_username: str
    status: BatchStatus
    contracts: tuple[BatchContract, ...]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        validation_id = str(self.validation_id).strip().casefold()
        source_file_name = str(self.source_file_name).strip()
        dependency = str(self.dependency).strip()
        created_by_username = str(self.created_by_username).strip()

        if len(validation_id) != 32 or any(
            character not in "0123456789abcdef" for character in validation_id
        ):
            raise ValueError("El identificador de validación no es válido.")
        if not source_file_name:
            raise ValueError("El archivo de origen es obligatorio.")
        if not dependency:
            raise ValueError("La dependencia del lote es obligatoria.")
        if self.created_by_user_id <= 0:
            raise ValueError("El usuario creador debe ser válido.")
        if not created_by_username:
            raise ValueError("El nombre del usuario creador es obligatorio.")
        if not isinstance(self.status, BatchStatus):
            raise TypeError("El estado del lote no es válido.")
        if not self.contracts:
            raise ValueError("El lote debe contener al menos un contrato.")

        row_numbers = [item.source_row_number for item in self.contracts]
        if len(row_numbers) != len(set(row_numbers)):
            raise ValueError("El lote no puede repetir filas de origen.")

        contract_identities = [
            item.contract.contract_number.strip().casefold()
            for item in self.contracts
        ]
        if len(contract_identities) != len(set(contract_identities)):
            raise ValueError("El lote no puede repetir números de contrato.")

        if any(
            item.contract.dependency.casefold() != dependency.casefold()
            for item in self.contracts
        ):
            raise ValueError(
                "Todos los contratos deben pertenecer a la dependencia del lote."
            )

        object.__setattr__(self, "validation_id", validation_id)
        object.__setattr__(self, "source_file_name", source_file_name)
        object.__setattr__(self, "dependency", dependency)
        object.__setattr__(self, "created_by_username", created_by_username)
        object.__setattr__(self, "created_at", _utc(self.created_at))
        object.__setattr__(self, "updated_at", _utc(self.updated_at))

    @property
    def selected_count(self) -> int:
        return len(self.contracts)
