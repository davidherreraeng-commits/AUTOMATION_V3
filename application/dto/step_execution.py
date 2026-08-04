from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from domain.enums import ContractStep
from domain.models import ContractExecution


class PortalVerificationStatus(str, Enum):
    """
    Resultado de verificar la postcondición de una etapa en el portal.
    """

    CONFIRMED = "CONFIRMED"
    NOT_APPLIED = "NOT_APPLIED"
    AMBIGUOUS = "AMBIGUOUS"


class StepExecutionOutcome(str, Enum):
    """
    Resultado de ejecutar o reconciliar una etapa.
    """

    STEP_CONFIRMED = "STEP_CONFIRMED"
    STEP_RECONCILED = "STEP_RECONCILED"

    RETRY_PENDING = "RETRY_PENDING"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FAILED = "FAILED"

    ALREADY_EXISTS = "ALREADY_EXISTS"
    COMPLETED = "COMPLETED"
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True, slots=True)
class PortalStepVerification:
    """
    Resultado estructurado de verificar una etapa en el portal.
    """

    step: ContractStep
    status: PortalVerificationStatus
    message: str | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.message is not None:
            normalized_message = self.message.strip()

            object.__setattr__(
                self,
                "message",
                normalized_message or None,
            )


@dataclass(frozen=True, slots=True)
class StepExecutionResult:
    """
    Resultado producido por StepExecutor.
    """

    execution: ContractExecution
    outcome: StepExecutionOutcome
    step: ContractStep | None = None
    message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome in {
            StepExecutionOutcome.STEP_CONFIRMED,
            StepExecutionOutcome.STEP_RECONCILED,
            StepExecutionOutcome.COMPLETED,
            StepExecutionOutcome.ALREADY_EXISTS,
        }

    @property
    def requires_attention(self) -> bool:
        return self.outcome in {
            StepExecutionOutcome.MANUAL_REVIEW,
            StepExecutionOutcome.FAILED,
        }