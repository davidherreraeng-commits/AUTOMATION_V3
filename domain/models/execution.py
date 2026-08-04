<<<<<<< HEAD
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.errors import ExecutionStateError


def utc_now() -> datetime:
    """Devuelve la fecha y hora actual con zona horaria UTC."""

    return datetime.now(timezone.utc)


def normalize_datetime(
    value: datetime | None,
) -> datetime | None:
    """
    Normaliza una fecha a UTC.

    Las fechas sin zona horaria se interpretan como UTC para evitar
    inconsistencias al restaurar ejecuciones desde persistencia.
    """

    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class ExecutionErrorInfo:
    """
    Información estructurada de un error ocurrido durante la ejecución.

    Esta entidad puede almacenarse directamente en el repositorio sin
    conservar la excepción original de Python.
    """

    code: str
    category: ErrorCategory
    message: str
    retryable: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        normalized_code = str(self.code).strip()
        normalized_message = str(self.message).strip()

        if not normalized_code:
            raise ValueError(
                "El código del error es obligatorio."
            )

        if not normalized_message:
            raise ValueError(
                "El mensaje del error es obligatorio."
            )

        if not isinstance(
            self.category,
            ErrorCategory,
        ):
            raise TypeError(
                "La categoría debe ser una instancia "
                "de ErrorCategory."
            )

        object.__setattr__(
            self,
            "code",
            normalized_code,
        )

        object.__setattr__(
            self,
            "message",
            normalized_message,
        )

        object.__setattr__(
            self,
            "retryable",
            bool(self.retryable),
        )

        object.__setattr__(
            self,
            "metadata",
            dict(self.metadata),
        )


@dataclass(slots=True)
class ContractExecution:
    """
    Agregado que representa la ejecución de un contrato.

    Contiene el estado necesario para:

    - Registrar intentos.
    - Guardar checkpoints.
    - Reanudar una automatización.
    - Identificar la etapa actualmente abierta.
    - Clasificar errores.
    - Finalizar ejecuciones exitosas o terminales.
    """

    execution_id: UUID

    contract_number: str
    dependency: str

    status: ExecutionStatus = ExecutionStatus.PENDING

    last_completed_step: ContractStep = (
        ContractStep.PENDING
    )

    current_step: ContractStep | None = None
    last_failed_step: ContractStep | None = None

    attempt_count: int = 0
    portal_profile: str | None = None

    last_error: ExecutionErrorInfo | None = None

    created_at: datetime = field(
        default_factory=utc_now
    )

    started_at: datetime | None = None

    updated_at: datetime = field(
        default_factory=utc_now
    )

    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self._normalize_identity()
        self._normalize_profile()
        self._normalize_dates()
        self._validate_initial_state()

    @classmethod
    def create(
        cls,
        *,
        contract_number: str,
        dependency: str,
    ) -> ContractExecution:
        """
        Crea una ejecución nueva en estado PENDING.
        """

        now = utc_now()

        return cls(
            execution_id=uuid4(),
            contract_number=contract_number,
            dependency=dependency,
            status=ExecutionStatus.PENDING,
            last_completed_step=ContractStep.PENDING,
            current_step=None,
            last_failed_step=None,
            attempt_count=0,
            portal_profile=None,
            last_error=None,
            created_at=now,
            started_at=None,
            updated_at=now,
            completed_at=None,
        )

    def start_attempt(
        self,
        portal_profile: str | None = None,
    ) -> None:
        """
        Inicia un nuevo intento de automatización.

        Solamente puede iniciarse desde:

        - PENDING
        - RETRY_PENDING
        """

        allowed_statuses = {
            ExecutionStatus.PENDING,
            ExecutionStatus.RETRY_PENDING,
        }

        if self.status not in allowed_statuses:
            raise ExecutionStateError(
                "No es posible iniciar un intento desde el estado "
                f"{self.status.value}.",
                status=self.status,
            )

        now = utc_now()

        self.status = ExecutionStatus.RUNNING
        self.attempt_count += 1

        if self.started_at is None:
            self.started_at = now

        if portal_profile is not None:
            normalized_profile = str(
                portal_profile
            ).strip()

            self.portal_profile = (
                normalized_profile or None
            )

        self.current_step = None
        self.last_failed_step = None
        self.last_error = None
        self.completed_at = None
        self.updated_at = now

    def _begin_step(
        self,
        step: ContractStep,
    ) -> None:
        """
        Abre una etapa operacional.

        Debe ser invocado únicamente por ContractStateMachine.
        """

        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para "
                "iniciar una etapa.",
                status=self.status,
            )

        if self.current_step is not None:
            raise ExecutionStateError(
                "Ya existe una etapa abierta: "
                f"{self.current_step.value}.",
                status=self.status,
            )

        if step in {
            ContractStep.PENDING,
            ContractStep.COMPLETED,
        }:
            raise ExecutionStateError(
                "La etapa solicitada no es una etapa "
                f"operacional válida: {step.value}.",
                status=self.status,
            )

        self.current_step = step
        self.updated_at = utc_now()

    def _confirm_step(
        self,
        step: ContractStep,
    ) -> None:
        """
        Confirma la etapa actualmente abierta.

        Debe ser invocado únicamente después de verificar la
        postcondición correspondiente en el portal.
        """

        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para "
                "confirmar una etapa.",
                status=self.status,
            )

        if self.current_step is None:
            raise ExecutionStateError(
                "No existe una etapa abierta para confirmar.",
                status=self.status,
            )

        if self.current_step is not step:
            raise ExecutionStateError(
                "La etapa que se intenta confirmar no coincide "
                "con la etapa actualmente abierta. "
                f"Abierta: {self.current_step.value}. "
                f"Recibida: {step.value}.",
                status=self.status,
            )

        self.last_completed_step = step
        self.current_step = None
        self.last_failed_step = None
        self.last_error = None
        self.updated_at = utc_now()

    def mark_retry_pending(
        self,
        error: ExecutionErrorInfo,
    ) -> None:
        """
        Registra un error recuperable y conserva el último checkpoint.

        La etapa que estaba abierta se almacena en last_failed_step.
        """

        self._require_running(
            operation=(
                "marcar la ejecución como pendiente "
                "de reintento"
            )
        )

        if not error.retryable:
            raise ExecutionStateError(
            "Un error no recuperable no puede producir "
            "el estado RETRY_PENDING.",
            status=self.status,
            )

        if self.current_step is not None:
            self.last_failed_step = self.current_step

        self.status = ExecutionStatus.RETRY_PENDING
        self.current_step = None
        self.last_error = error
        self.completed_at = None
        self.updated_at = utc_now()

    def mark_failed(
        self,
        error: ExecutionErrorInfo,
    ) -> None:
        """
        Finaliza la ejecución como fallida.

        Un error recuperable también puede terminar en FAILED cuando
        la política de reintentos haya agotado sus oportunidades.
        """

        self._require_running(
            operation=(
                "marcar la ejecución como fallida"
            )
        )

        if self.current_step is not None:
            self.last_failed_step = self.current_step

        now = utc_now()

        self.status = ExecutionStatus.FAILED
        self.current_step = None
        self.last_error = error
        self.completed_at = now
        self.updated_at = now

    def mark_manual_review(
        self,
        error: ExecutionErrorInfo,
    ) -> None:
        """
        Detiene la automatización y exige intervención humana.
        """

        self._require_running(
            operation=(
                "enviar la ejecución a revisión manual"
            )
        )

        if self.current_step is not None:
            self.last_failed_step = self.current_step

        now = utc_now()

        self.status = ExecutionStatus.MANUAL_REVIEW
        self.current_step = None
        self.last_error = error
        self.completed_at = now
        self.updated_at = now

    def mark_already_exists(
        self,
        message: str,
    ) -> None:
        """
        Finaliza la ejecución porque el contrato ya existe en el portal.

        ALREADY_EXISTS es un estado terminal, aunque la automatización
        no haya recorrido todas las etapas.
        """

        self._require_running(
            operation=(
                "marcar el contrato como existente"
            )
        )

        normalized_message = str(message).strip()

        if not normalized_message:
            raise ValueError(
                "El mensaje que confirma la existencia "
                "del contrato es obligatorio."
            )

        now = utc_now()

        self.status = ExecutionStatus.ALREADY_EXISTS
        self.current_step = None
        self.last_failed_step = None

        self.last_error = ExecutionErrorInfo(
            code="CONTRACT_ALREADY_EXISTS",
            category=ErrorCategory.BUSINESS_RULE,
            message=normalized_message,
            retryable=False,
            metadata={},
        )

        self.completed_at = now
        self.updated_at = now

    def _mark_completed(self) -> None:
        """
        Finaliza exitosamente la ejecución.

        Debe ser invocado por ContractStateMachine después de confirmar
        la última etapa operacional.
        """

        self._require_running(
            operation=(
                "finalizar correctamente la ejecución"
            )
        )

        if self.current_step is not None:
            raise ExecutionStateError(
                "No se puede completar la ejecución mientras "
                f"exista una etapa abierta: "
                f"{self.current_step.value}.",
                status=self.status,
            )

        now = utc_now()

        self.status = ExecutionStatus.COMPLETED
        self.last_completed_step = ContractStep.COMPLETED
        self.current_step = None
        self.last_failed_step = None
        self.last_error = None
        self.completed_at = now
        self.updated_at = now

    def _require_running(
        self,
        *,
        operation: str,
    ) -> None:
        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para "
                f"{operation}. Estado actual: "
                f"{self.status.value}.",
                status=self.status,
            )

    def _normalize_identity(self) -> None:
        normalized_contract_number = str(
            self.contract_number
        ).strip()

        normalized_dependency = " ".join(
            str(self.dependency).split()
        )

        if not normalized_contract_number:
            raise ValueError(
                "El número del contrato es obligatorio."
            )

        if not normalized_dependency:
            raise ValueError(
                "La dependencia es obligatoria."
            )

        self.contract_number = normalized_contract_number
        self.dependency = normalized_dependency

    def _normalize_profile(self) -> None:
        if self.portal_profile is None:
            return

        normalized_profile = str(
            self.portal_profile
        ).strip()

        self.portal_profile = (
            normalized_profile or None
        )

    def _normalize_dates(self) -> None:
        normalized_created_at = normalize_datetime(
            self.created_at
        )

        normalized_updated_at = normalize_datetime(
            self.updated_at
        )

        if normalized_created_at is None:
            normalized_created_at = utc_now()

        if normalized_updated_at is None:
            normalized_updated_at = (
                normalized_created_at
            )

        self.created_at = normalized_created_at
        self.updated_at = normalized_updated_at

        self.started_at = normalize_datetime(
            self.started_at
        )

        self.completed_at = normalize_datetime(
            self.completed_at
        )

    def _validate_initial_state(self) -> None:
        if not isinstance(
            self.execution_id,
            UUID,
        ):
            raise TypeError(
                "execution_id debe ser una instancia de UUID."
            )

        if not isinstance(
            self.status,
            ExecutionStatus,
        ):
            raise TypeError(
                "status debe ser una instancia de "
                "ExecutionStatus."
            )

        if not isinstance(
            self.last_completed_step,
            ContractStep,
        ):
            raise TypeError(
                "last_completed_step debe ser una instancia "
                "de ContractStep."
            )

        if (
            self.current_step is not None
            and not isinstance(
                self.current_step,
                ContractStep,
            )
        ):
            raise TypeError(
                "current_step debe ser ContractStep o None."
            )

        if (
            self.last_failed_step is not None
            and not isinstance(
                self.last_failed_step,
                ContractStep,
            )
        ):
            raise TypeError(
                "last_failed_step debe ser ContractStep o None."
            )

        if self.attempt_count < 0:
            raise ValueError(
                "La cantidad de intentos no puede ser negativa."
            )

        if (
            self.last_error is not None
            and not isinstance(
                self.last_error,
                ExecutionErrorInfo,
            )
        ):
            raise TypeError(
                "last_error debe ser ExecutionErrorInfo o None."
=======
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from domain.enums import (
    ContractStep,
    ErrorCategory,
    ExecutionStatus,
)
from domain.errors import ExecutionStateError


def utc_now() -> datetime:
    """Devuelve la fecha y hora actual con zona horaria UTC."""

    return datetime.now(timezone.utc)


def normalize_datetime(
    value: datetime | None,
) -> datetime | None:
    """
    Normaliza una fecha a UTC.

    Las fechas sin zona horaria se interpretan como UTC para evitar
    inconsistencias al restaurar ejecuciones desde persistencia.
    """

    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class ExecutionErrorInfo:
    """
    Información estructurada de un error ocurrido durante la ejecución.

    Esta entidad puede almacenarse directamente en el repositorio sin
    conservar la excepción original de Python.
    """

    code: str
    category: ErrorCategory
    message: str
    retryable: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        normalized_code = str(self.code).strip()
        normalized_message = str(self.message).strip()

        if not normalized_code:
            raise ValueError(
                "El código del error es obligatorio."
            )

        if not normalized_message:
            raise ValueError(
                "El mensaje del error es obligatorio."
            )

        if not isinstance(
            self.category,
            ErrorCategory,
        ):
            raise TypeError(
                "La categoría debe ser una instancia "
                "de ErrorCategory."
            )

        object.__setattr__(
            self,
            "code",
            normalized_code,
        )

        object.__setattr__(
            self,
            "message",
            normalized_message,
        )

        object.__setattr__(
            self,
            "retryable",
            bool(self.retryable),
        )

        object.__setattr__(
            self,
            "metadata",
            dict(self.metadata),
        )


@dataclass(slots=True)
class ContractExecution:
    """
    Agregado que representa la ejecución de un contrato.

    Contiene el estado necesario para:

    - Registrar intentos.
    - Guardar checkpoints.
    - Reanudar una automatización.
    - Identificar la etapa actualmente abierta.
    - Clasificar errores.
    - Finalizar ejecuciones exitosas o terminales.
    """

    execution_id: UUID

    contract_number: str
    dependency: str

    status: ExecutionStatus = ExecutionStatus.PENDING

    last_completed_step: ContractStep = (
        ContractStep.PENDING
    )

    current_step: ContractStep | None = None
    last_failed_step: ContractStep | None = None

    attempt_count: int = 0
    portal_profile: str | None = None

    last_error: ExecutionErrorInfo | None = None

    created_at: datetime = field(
        default_factory=utc_now
    )

    started_at: datetime | None = None

    updated_at: datetime = field(
        default_factory=utc_now
    )

    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self._normalize_identity()
        self._normalize_profile()
        self._normalize_dates()
        self._validate_initial_state()

    @classmethod
    def create(
        cls,
        *,
        contract_number: str,
        dependency: str,
    ) -> ContractExecution:
        """
        Crea una ejecución nueva en estado PENDING.
        """

        now = utc_now()

        return cls(
            execution_id=uuid4(),
            contract_number=contract_number,
            dependency=dependency,
            status=ExecutionStatus.PENDING,
            last_completed_step=ContractStep.PENDING,
            current_step=None,
            last_failed_step=None,
            attempt_count=0,
            portal_profile=None,
            last_error=None,
            created_at=now,
            started_at=None,
            updated_at=now,
            completed_at=None,
        )

    def start_attempt(
        self,
        portal_profile: str | None = None,
    ) -> None:
        """
        Inicia un nuevo intento de automatización.

        Solamente puede iniciarse desde:

        - PENDING
        - RETRY_PENDING
        """

        allowed_statuses = {
            ExecutionStatus.PENDING,
            ExecutionStatus.RETRY_PENDING,
        }

        if self.status not in allowed_statuses:
            raise ExecutionStateError(
                "No es posible iniciar un intento desde el estado "
                f"{self.status.value}.",
                status=self.status,
            )

        now = utc_now()

        self.status = ExecutionStatus.RUNNING
        self.attempt_count += 1

        if self.started_at is None:
            self.started_at = now

        if portal_profile is not None:
            normalized_profile = str(
                portal_profile
            ).strip()

            self.portal_profile = (
                normalized_profile or None
            )

        self.current_step = None
        self.last_failed_step = None
        self.last_error = None
        self.completed_at = None
        self.updated_at = now

    def _begin_step(
        self,
        step: ContractStep,
    ) -> None:
        """
        Abre una etapa operacional.

        Debe ser invocado únicamente por ContractStateMachine.
        """

        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para "
                "iniciar una etapa.",
                status=self.status,
            )

        if self.current_step is not None:
            raise ExecutionStateError(
                "Ya existe una etapa abierta: "
                f"{self.current_step.value}.",
                status=self.status,
            )

        if step in {
            ContractStep.PENDING,
            ContractStep.COMPLETED,
        }:
            raise ExecutionStateError(
                "La etapa solicitada no es una etapa "
                f"operacional válida: {step.value}.",
                status=self.status,
            )

        self.current_step = step
        self.updated_at = utc_now()

    def _confirm_step(
        self,
        step: ContractStep,
    ) -> None:
        """
        Confirma la etapa actualmente abierta.

        Debe ser invocado únicamente después de verificar la
        postcondición correspondiente en el portal.
        """

        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para "
                "confirmar una etapa.",
                status=self.status,
            )

        if self.current_step is None:
            raise ExecutionStateError(
                "No existe una etapa abierta para confirmar.",
                status=self.status,
            )

        if self.current_step is not step:
            raise ExecutionStateError(
                "La etapa que se intenta confirmar no coincide "
                "con la etapa actualmente abierta. "
                f"Abierta: {self.current_step.value}. "
                f"Recibida: {step.value}.",
                status=self.status,
            )

        self.last_completed_step = step
        self.current_step = None
        self.last_failed_step = None
        self.last_error = None
        self.updated_at = utc_now()

    def mark_retry_pending(
        self,
        error: ExecutionErrorInfo,
    ) -> None:
        """
        Registra un error recuperable y conserva el último checkpoint.

        La etapa que estaba abierta se almacena en last_failed_step.
        """

        self._require_running(
            operation=(
                "marcar la ejecución como pendiente "
                "de reintento"
            )
        )

        if not error.retryable:
            raise ExecutionStateError(
            "Un error no recuperable no puede producir "
            "el estado RETRY_PENDING.",
            status=self.status,
            )

        if self.current_step is not None:
            self.last_failed_step = self.current_step

        self.status = ExecutionStatus.RETRY_PENDING
        self.current_step = None
        self.last_error = error
        self.completed_at = None
        self.updated_at = utc_now()

    def mark_failed(
        self,
        error: ExecutionErrorInfo,
    ) -> None:
        """
        Finaliza la ejecución como fallida.

        Un error recuperable también puede terminar en FAILED cuando
        la política de reintentos haya agotado sus oportunidades.
        """

        self._require_running(
            operation=(
                "marcar la ejecución como fallida"
            )
        )

        if self.current_step is not None:
            self.last_failed_step = self.current_step

        now = utc_now()

        self.status = ExecutionStatus.FAILED
        self.current_step = None
        self.last_error = error
        self.completed_at = now
        self.updated_at = now

    def mark_manual_review(
        self,
        error: ExecutionErrorInfo,
    ) -> None:
        """
        Detiene la automatización y exige intervención humana.
        """

        self._require_running(
            operation=(
                "enviar la ejecución a revisión manual"
            )
        )

        if self.current_step is not None:
            self.last_failed_step = self.current_step

        now = utc_now()

        self.status = ExecutionStatus.MANUAL_REVIEW
        self.current_step = None
        self.last_error = error
        self.completed_at = now
        self.updated_at = now

    def mark_already_exists(
        self,
        message: str,
    ) -> None:
        """
        Finaliza la ejecución porque el contrato ya existe en el portal.

        ALREADY_EXISTS es un estado terminal, aunque la automatización
        no haya recorrido todas las etapas.
        """

        self._require_running(
            operation=(
                "marcar el contrato como existente"
            )
        )

        normalized_message = str(message).strip()

        if not normalized_message:
            raise ValueError(
                "El mensaje que confirma la existencia "
                "del contrato es obligatorio."
            )

        now = utc_now()

        self.status = ExecutionStatus.ALREADY_EXISTS
        self.current_step = None
        self.last_failed_step = None

        self.last_error = ExecutionErrorInfo(
            code="CONTRACT_ALREADY_EXISTS",
            category=ErrorCategory.BUSINESS_RULE,
            message=normalized_message,
            retryable=False,
            metadata={},
        )

        self.completed_at = now
        self.updated_at = now

    def _mark_completed(self) -> None:
        """
        Finaliza exitosamente la ejecución.

        Debe ser invocado por ContractStateMachine después de confirmar
        la última etapa operacional.
        """

        self._require_running(
            operation=(
                "finalizar correctamente la ejecución"
            )
        )

        if self.current_step is not None:
            raise ExecutionStateError(
                "No se puede completar la ejecución mientras "
                f"exista una etapa abierta: "
                f"{self.current_step.value}.",
                status=self.status,
            )

        now = utc_now()

        self.status = ExecutionStatus.COMPLETED
        self.last_completed_step = ContractStep.COMPLETED
        self.current_step = None
        self.last_failed_step = None
        self.last_error = None
        self.completed_at = now
        self.updated_at = now

    def _require_running(
        self,
        *,
        operation: str,
    ) -> None:
        if self.status is not ExecutionStatus.RUNNING:
            raise ExecutionStateError(
                "La ejecución debe estar en RUNNING para "
                f"{operation}. Estado actual: "
                f"{self.status.value}.",
                status=self.status,
            )

    def _normalize_identity(self) -> None:
        normalized_contract_number = str(
            self.contract_number
        ).strip()

        normalized_dependency = " ".join(
            str(self.dependency).split()
        )

        if not normalized_contract_number:
            raise ValueError(
                "El número del contrato es obligatorio."
            )

        if not normalized_dependency:
            raise ValueError(
                "La dependencia es obligatoria."
            )

        self.contract_number = normalized_contract_number
        self.dependency = normalized_dependency

    def _normalize_profile(self) -> None:
        if self.portal_profile is None:
            return

        normalized_profile = str(
            self.portal_profile
        ).strip()

        self.portal_profile = (
            normalized_profile or None
        )

    def _normalize_dates(self) -> None:
        normalized_created_at = normalize_datetime(
            self.created_at
        )

        normalized_updated_at = normalize_datetime(
            self.updated_at
        )

        if normalized_created_at is None:
            normalized_created_at = utc_now()

        if normalized_updated_at is None:
            normalized_updated_at = (
                normalized_created_at
            )

        self.created_at = normalized_created_at
        self.updated_at = normalized_updated_at

        self.started_at = normalize_datetime(
            self.started_at
        )

        self.completed_at = normalize_datetime(
            self.completed_at
        )

    def _validate_initial_state(self) -> None:
        if not isinstance(
            self.execution_id,
            UUID,
        ):
            raise TypeError(
                "execution_id debe ser una instancia de UUID."
            )

        if not isinstance(
            self.status,
            ExecutionStatus,
        ):
            raise TypeError(
                "status debe ser una instancia de "
                "ExecutionStatus."
            )

        if not isinstance(
            self.last_completed_step,
            ContractStep,
        ):
            raise TypeError(
                "last_completed_step debe ser una instancia "
                "de ContractStep."
            )

        if (
            self.current_step is not None
            and not isinstance(
                self.current_step,
                ContractStep,
            )
        ):
            raise TypeError(
                "current_step debe ser ContractStep o None."
            )

        if (
            self.last_failed_step is not None
            and not isinstance(
                self.last_failed_step,
                ContractStep,
            )
        ):
            raise TypeError(
                "last_failed_step debe ser ContractStep o None."
            )

        if self.attempt_count < 0:
            raise ValueError(
                "La cantidad de intentos no puede ser negativa."
            )

        if (
            self.last_error is not None
            and not isinstance(
                self.last_error,
                ExecutionErrorInfo,
            )
        ):
            raise TypeError(
                "last_error debe ser ExecutionErrorInfo o None."
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
            )