from __future__ import annotations

from enum import Enum


class BatchStatus(str, Enum):
    """Estado global de un lote de contratos."""

    READY = "READY"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchContractStatus(str, Enum):
    """Estado de un contrato individual dentro de un lote."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
