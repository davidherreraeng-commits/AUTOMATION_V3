from __future__ import annotations

from uuid import UUID


class ExecutionEvidenceNotFoundError(LookupError):
    def __init__(self, correlation_id: UUID) -> None:
        self.correlation_id = correlation_id
        super().__init__(
            f"No existe evidencia contractual para la correlación '{correlation_id}'."
        )


class ExecutionEvidenceContextError(PermissionError):
    """La evidencia no pertenece al lote, contrato o dependencia solicitados."""
