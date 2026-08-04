from __future__ import annotations

from uuid import UUID


class BatchContractExecutionError(RuntimeError):
    """Error base del control de ejecución de un contrato del lote."""


class BatchContractItemNotFoundError(BatchContractExecutionError):
    """El contrato seleccionado no pertenece al lote consultado."""

    def __init__(self, *, batch_id: UUID, item_id: UUID) -> None:
        self.batch_id = batch_id
        self.item_id = item_id
        super().__init__(
            "El contrato seleccionado no pertenece al lote indicado. "
            f"Lote: '{batch_id}'. Contrato: '{item_id}'."
        )


class BatchContractExecutionBlockedError(BatchContractExecutionError):
    """Una o más condiciones impiden iniciar la escritura real."""

    def __init__(
        self,
        issues: tuple[tuple[str, str], ...],
    ) -> None:
        self.issues = tuple(
            (str(code).strip().upper(), str(message).strip())
            for code, message in issues
            if str(code).strip() and str(message).strip()
        )
        detail = " ".join(message for _, message in self.issues)
        super().__init__(
            detail
            or "El contrato no cumple las condiciones de ejecución."
        )


class BatchContractExecutionConfirmationError(
    BatchContractExecutionError
):
    """La frase de confirmación no autoriza la escritura solicitada."""

    def __init__(self, required_confirmation: str) -> None:
        self.required_confirmation = str(required_confirmation).strip()
        super().__init__(
            "La confirmación de escritura real no coincide. "
            f"Escriba exactamente: {self.required_confirmation}"
        )


class BatchContractExecutionInProgressError(
    BatchContractExecutionError
):
    """Ya existe una ejecución contractual activa en este proceso."""

    def __init__(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
    ) -> None:
        self.batch_id = batch_id
        self.item_id = item_id
        super().__init__(
            "Ya existe una ejecución contractual activa. "
            f"Lote: '{batch_id}'. Contrato: '{item_id}'."
        )


class BatchContractExecutionIdentityError(
    BatchContractExecutionError
):
    """El execution_id no corresponde al contrato seleccionado."""


class BatchContractExecutionStateError(
    BatchContractExecutionError
):
    """El estado persistido no permite la operación solicitada."""
