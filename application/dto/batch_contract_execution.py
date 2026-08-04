from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.enums import (
    ContractStep,
    ExecutionMode,
    ExecutionStatus,
    RealWriteAuthorizationStatus,
)
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.models import ContractExecution
from domain.models.contract_batch import BatchContract, ContractBatch
from application.dto.step_execution import StepExecutionResult


@dataclass(frozen=True, slots=True)
class BatchContractExecutionIssue:
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
class BatchContractExecutionPreflight:
    batch: ContractBatch
    item: BatchContract
    required_confirmation: str
    execution_enabled: bool
    executor_available: bool
    credentials_configured: bool
    credentials_recently_tested: bool
    active_in_process: bool
    execution: ContractExecution | None
    resumable: bool
    checked_at: datetime
    issues: tuple[BatchContractExecutionIssue, ...]
    mode: ExecutionMode = ExecutionMode.REAL
    real_write_enabled: bool = False
    simulation_available: bool = False
    latest_correlation_id: UUID | None = None
    real_write_authorization_required: bool = False
    authorization_available: bool = False
    authorization_id: UUID | None = None
    authorization_status: RealWriteAuthorizationStatus | None = None
    authorization_expires_at: datetime | None = None
    authorization_required_confirmation: str | None = None
    authorization_ttl_seconds: int | None = None

    @property
    def can_execute(self) -> bool:
        return not any(issue.blocking for issue in self.issues)


@dataclass(frozen=True, slots=True)
class BatchContractExecutionResult:
    batch: ContractBatch
    item: BatchContract
    required_confirmation: str
    active_in_process: bool
    execution: ContractExecution | None
    transition_count: int
    success: bool
    resumable: bool
    retry_pending: bool
    requires_manual_review: bool
    operational_message: str
    error_code: str | None = None
    technical_detail: str | None = None
    mode: ExecutionMode = ExecutionMode.REAL
    correlation_id: UUID | None = None
    writes_to_portal: bool = True
    evidence_count: int = 0
    authorization_id: UUID | None = None
    authorization_consumed_at: datetime | None = None
    transitions: tuple[StepExecutionResult, ...] = ()

    @property
    def batch_status(self) -> BatchStatus:
        return self.batch.status

    @property
    def item_status(self) -> BatchContractStatus:
        return self.item.status

    @property
    def execution_id(self) -> UUID | None:
        if self.execution is None:
            return None
        return self.execution.execution_id

    @property
    def execution_status(self) -> ExecutionStatus | None:
        if self.execution is None:
            return None
        return self.execution.status

    @property
    def last_completed_step(self) -> ContractStep | None:
        if self.execution is None:
            return None
        return self.execution.last_completed_step

    @property
    def current_step(self) -> ContractStep | None:
        if self.execution is None:
            return None
        return self.execution.current_step

    @property
    def last_failed_step(self) -> ContractStep | None:
        if self.execution is None:
            return None
        return self.execution.last_failed_step

    @property
    def attempt_count(self) -> int:
        if self.execution is None:
            return 0
        return self.execution.attempt_count

    @property
    def checkpoint_updated_at(self) -> datetime | None:
        if self.execution is None:
            return None
        return self.execution.updated_at
