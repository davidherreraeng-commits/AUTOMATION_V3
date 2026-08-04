from __future__ import annotations


class BatchManagementError(Exception):
    """Error base de preparación y persistencia de lotes."""


class StoredValidationNotFoundError(BatchManagementError):
    def __init__(self, validation_id: str) -> None:
        super().__init__(
            f"No existe una validación disponible con identificador '{validation_id}'."
        )


class StoredValidationCorruptedError(BatchManagementError):
    """El archivo o manifiesto de una validación almacenada no es consistente."""


class InvalidBatchSelectionError(BatchManagementError):
    """La selección contiene filas vacías, repetidas, inválidas o inexistentes."""


class BatchAlreadyExistsError(BatchManagementError):
    def __init__(self, validation_id: str) -> None:
        super().__init__(
            "La validación ya fue convertida en un lote. "
            f"Identificador: {validation_id}."
        )


class BatchNotFoundError(BatchManagementError):
    def __init__(self, batch_id: str) -> None:
        super().__init__(f"No existe el lote solicitado: {batch_id}.")


class BatchRepositoryError(BatchManagementError):
    """Fallo técnico de persistencia del lote."""
