from __future__ import annotations

from typing import Protocol
from uuid import UUID

from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.models.contract_batch import ContractBatch


class BatchRepository(Protocol):
    """Persistencia de lotes preparados y su progreso de ejecución."""

    def create(self, batch: ContractBatch) -> ContractBatch:
        ...

    def get_by_id(
        self,
        batch_id: UUID,
        *,
        dependency: str,
    ) -> ContractBatch | None:
        ...

    def get_by_validation(
        self,
        validation_id: str,
        *,
        dependency: str,
    ) -> ContractBatch | None:
        ...

    def list_by_dependency(
        self,
        dependency: str,
        *,
        limit: int = 50,
    ) -> tuple[ContractBatch, ...]:
        ...

    def get_processing_by_dependency(
        self,
        dependency: str,
    ) -> ContractBatch | None:
        ...

    def claim_for_processing(
        self,
        batch_id: UUID,
        *,
        dependency: str,
    ) -> ContractBatch:
        ...

    def update_contract_status(
        self,
        batch_id: UUID,
        item_id: UUID,
        *,
        dependency: str,
        status: BatchContractStatus,
        message: str | None = None,
    ) -> ContractBatch:
        ...

    def finish_processing(
        self,
        batch_id: UUID,
        *,
        dependency: str,
        status: BatchStatus,
    ) -> ContractBatch:
        ...

    def cancel_ready(
        self,
        batch_id: UUID,
        *,
        dependency: str,
    ) -> ContractBatch:
        ...
