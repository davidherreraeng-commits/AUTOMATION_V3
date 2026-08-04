from __future__ import annotations


class BatchExecutionError(Exception):
    """Error base del control de ejecución de lotes."""


class BatchExecutionBlockedError(BatchExecutionError):
    """El preflight contiene una o más condiciones bloqueantes."""

    def __init__(self, messages: list[str] | tuple[str, ...]) -> None:
        normalized = [str(message).strip() for message in messages if str(message).strip()]
        detail = " ".join(normalized) or "El lote no cumple las condiciones de ejecución."
        super().__init__(detail)


class BatchExecutionInProgressError(BatchExecutionError):
    def __init__(self, dependency: str) -> None:
        super().__init__(
            "Ya existe un lote en ejecución para la dependencia "
            f"'{str(dependency).strip()}'."
        )


class BatchNotReadyForExecutionError(BatchExecutionError):
    def __init__(self, status: str) -> None:
        super().__init__(
            "El lote debe estar en estado READY para iniciar la ejecución. "
            f"Estado actual: {status}."
        )


class BatchExecutionStateError(BatchExecutionError):
    """La transición solicitada no es válida para el estado persistido."""
