from __future__ import annotations

from typing import Any, Mapping

from domain.enums import ErrorCategory


class PortalAutomationError(Exception):
    """
    Error base para las excepciones producidas durante la
    automatización del portal.

    Estos datos permiten convertir posteriormente la excepción en un
    ExecutionErrorInfo y persistirla en el checkpoint.
    """

    default_code = "PORTAL_AUTOMATION_ERROR"
    default_category = ErrorCategory.UNKNOWN
    default_retryable = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        category: ErrorCategory | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        normalized_message = str(message).strip()

        if not normalized_message:
            raise ValueError(
                "El mensaje del error del portal es obligatorio."
            )

        self.code = code or self.default_code
        self.category = category or self.default_category

        self.retryable = (
            self.default_retryable
            if retryable is None
            else bool(retryable)
        )

        self.metadata = dict(metadata or {})

        super().__init__(normalized_message)


class PortalTimeoutError(PortalAutomationError):
    """El portal no respondió dentro del tiempo esperado."""

    default_code = "PORTAL_TIMEOUT"
    default_category = ErrorCategory.TIMEOUT
    default_retryable = True


class PortalSessionExpiredError(PortalAutomationError):
    """La sesión del usuario expiró o dejó de ser válida."""

    default_code = "PORTAL_SESSION_EXPIRED"
    default_category = ErrorCategory.SESSION
    default_retryable = True


class PortalValidationError(PortalAutomationError):
    """El portal rechazó los datos ingresados."""

    default_code = "PORTAL_VALIDATION_ERROR"
    default_category = ErrorCategory.PORTAL_VALIDATION
    default_retryable = False


class PortalStructureChangedError(PortalAutomationError):
    """La estructura esperada del portal cambió."""

    default_code = "PORTAL_STRUCTURE_CHANGED"
    default_category = ErrorCategory.PORTAL_STRUCTURE
    default_retryable = False


class PortalEntityNotFoundError(PortalAutomationError):
    """No se encontró una entidad necesaria en el portal."""

    default_code = "PORTAL_ENTITY_NOT_FOUND"
    default_category = ErrorCategory.BUSINESS_RULE
    default_retryable = False


class PortalAlreadyExistsError(PortalAutomationError):
    """El contrato ya existe en Gestión Transparente."""

    default_code = "CONTRACT_ALREADY_EXISTS"
    default_category = ErrorCategory.BUSINESS_RULE
    default_retryable = False