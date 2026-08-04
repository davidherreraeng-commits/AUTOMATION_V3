from __future__ import annotations

from typing import Protocol
from uuid import UUID

from application.dto.execution_evidence import ContractExecutionEvidence
from domain.enums import ExecutionMode


class ExecutionEvidenceRepositoryError(RuntimeError):
    """Error de persistencia de evidencias contractuales."""


class ExecutionEvidenceRepository(Protocol):
    def initialize(self) -> None:
        ...

    def save(self, evidence: ContractExecutionEvidence) -> None:
        ...

    def get(self, correlation_id: UUID) -> ContractExecutionEvidence | None:
        ...

    def get_latest(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        mode: ExecutionMode | None = None,
    ) -> ContractExecutionEvidence | None:
        ...

    def list_for_item(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
    ) -> tuple[ContractExecutionEvidence, ...]:
        ...
