from enum import Enum


class ExecutionMode(str, Enum):
    """Modo de una ejecución contractual controlada."""

    DRY_RUN = "DRY_RUN"
    REAL = "REAL"
