from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from domain.models import ContractData

if TYPE_CHECKING:
    from application.use_cases.process_contract import ContractProcessingResult


class ContractExecutor(Protocol):
    """Ejecuta o reanuda un contrato dentro de una sesión controlada."""

    def execute(
        self,
        *,
        contract: ContractData,
        execution_id: UUID | None = None,
    ) -> ContractProcessingResult:
        ...
