from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.enums.batch_status import BatchStatus


@dataclass(frozen=True, slots=True)
class BatchExecutionPreflightIssue:
    code: str
    message: str
    blocking: bool = True

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "blocking", bool(self.blocking))


@dataclass(frozen=True, slots=True)
class BatchExecutionPreflight:
    batch_id: UUID
    batch_status: BatchStatus
    dependency: str
    runner_name: str
    execution_enabled: bool
    runner_available: bool
    credentials_configured: bool
    credentials_recently_tested: bool
    active_batch_id: UUID | None
    checked_at: datetime
    issues: tuple[BatchExecutionPreflightIssue, ...]

    @property
    def can_execute(self) -> bool:
        return not any(issue.blocking for issue in self.issues)
