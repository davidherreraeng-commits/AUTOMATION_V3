from __future__ import annotations

from typing import Literal

from selenium.common.exceptions import (
    TimeoutException,
)
from selenium.webdriver.remote.webelement import (
    WebElement,
)

from adapters.portal.gestion_transparente.locators import (
    LocatorRegistry,
    LocatorSpec,
)
from adapters.portal.gestion_transparente.selenium.diagnostics import (
    BrowserDiagnostics,
)
from adapters.portal.gestion_transparente.selenium.waits import (
    SeleniumWaits,
)
from domain.errors import PortalTimeoutError


ResolutionCondition = Literal[
    "presence",
    "visible",
    "clickable",
]


class ElementResolver:
    """
    Resuelve elementos por claves semánticas y fallbacks.

    Cuando todos los candidatos fallan puede capturar evidencia
    automática del navegador.
    """

    def __init__(
        self,
        *,
        registry: LocatorRegistry,
        waits: SeleniumWaits,
        diagnostics: BrowserDiagnostics | None = None,
    ) -> None:
        self._registry = registry
        self._waits = waits
        self._diagnostics = diagnostics

    def presence(
        self,
        key: str,
        *,
        timeout_seconds: float | None = None,
    ) -> WebElement:
        return self.resolve(
            key,
            condition="presence",
            timeout_seconds=timeout_seconds,
        )

    def visible(
        self,
        key: str,
        *,
        timeout_seconds: float | None = None,
    ) -> WebElement:
        return self.resolve(
            key,
            condition="visible",
            timeout_seconds=timeout_seconds,
        )

    def clickable(
        self,
        key: str,
        *,
        timeout_seconds: float | None = None,
    ) -> WebElement:
        return self.resolve(
            key,
            condition="clickable",
            timeout_seconds=timeout_seconds,
        )

    def optional_visible(
        self,
        key: str,
        *,
        timeout_seconds: float = 2.0,
    ) -> WebElement | None:
        """
        Las búsquedas opcionales no generan diagnósticos.
        """

        try:
            return self.resolve(
                key,
                condition="visible",
                timeout_seconds=timeout_seconds,
                capture_diagnostics=False,
            )

        except PortalTimeoutError:
            return None

    def resolve(
        self,
        key: str,
        *,
        condition: ResolutionCondition = "visible",
        timeout_seconds: float | None = None,
        capture_diagnostics: bool = True,
    ) -> WebElement:
        candidates = self._registry.candidates(
            key
        )

        total_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else self._waits.default_timeout_seconds
        )

        if total_timeout <= 0:
            raise ValueError(
                "El timeout total debe ser mayor que cero."
            )

        timeout_per_candidate = max(
            total_timeout / len(candidates),
            self._waits.poll_frequency_seconds,
        )

        attempts: list[dict[str, object]] = []

        for candidate in candidates:
            try:
                return self._resolve_candidate(
                    candidate,
                    condition=condition,
                    timeout_seconds=(
                        timeout_per_candidate
                    ),
                )

            except TimeoutException as error:
                attempts.append(
                    {
                        "by": candidate.by,
                        "value": candidate.value,
                        "priority": candidate.priority,
                        "error": str(error),
                    }
                )

        error_metadata: dict[str, object] = {
            "locator_key": key,
            "condition": condition,
            "timeout_seconds": total_timeout,
            "attempts": attempts,
        }

        if (
            capture_diagnostics
            and self._diagnostics is not None
        ):
            try:
                evidence = (
                    self._diagnostics.capture(
                        event=f"locator_{key}",
                        metadata=error_metadata,
                    )
                )

                error_metadata["diagnostics"] = (
                    evidence.as_metadata()
                )

            except Exception as diagnostic_error:
                error_metadata[
                    "diagnostics_error"
                ] = (
                    f"{type(diagnostic_error).__name__}: "
                    f"{diagnostic_error}"
                )

        raise PortalTimeoutError(
            "No fue posible resolver el elemento "
            f"'{key}' mediante ninguno de sus "
            "localizadores.",
            metadata=error_metadata,
        )

    def _resolve_candidate(
        self,
        candidate: LocatorSpec,
        *,
        condition: ResolutionCondition,
        timeout_seconds: float,
    ) -> WebElement:
        if condition == "presence":
            return self._waits.presence(
                candidate.locator,
                timeout_seconds=timeout_seconds,
            )

        if condition == "visible":
            return self._waits.visible(
                candidate.locator,
                timeout_seconds=timeout_seconds,
            )

        if condition == "clickable":
            return self._waits.clickable(
                candidate.locator,
                timeout_seconds=timeout_seconds,
            )

        raise ValueError(
            "Condición de resolución no soportada: "
            f"{condition}."
        )