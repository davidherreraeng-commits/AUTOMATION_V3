from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from adapters.portal.gestion_transparente.selenium.element_resolver import (
    ElementResolver,
)
from adapters.portal.gestion_transparente.selenium.waits import SeleniumWaits
from domain.errors import PortalTimeoutError


ClickMode = Literal["native", "actions", "javascript"]
SelectionPostcondition = Callable[[WebDriver], bool]


@dataclass(frozen=True, slots=True)
class VerifiedSelectionPolicy:
    """Política común para selecciones desde resultados de búsqueda MUI.

    Gestión Transparente puede usar los primeros clics para enfocar o activar
    una fila sin trasladar todavía el valor al formulario principal. La
    selección solo se considera exitosa cuando se cumple una postcondición
    semántica fuera del diálogo.
    """

    click_modes: tuple[ClickMode, ...] = (
        "native",
        "native",
        "native",
        "actions",
        "javascript",
        "native",
    )
    resolve_timeout_seconds: float = 5.0
    postcondition_timeout_seconds: float = 3.0
    final_postcondition_timeout_seconds: float = 4.0

    def __post_init__(self) -> None:
        if not self.click_modes:
            raise ValueError("La política debe incluir al menos un clic.")
        if self.resolve_timeout_seconds <= 0:
            raise ValueError("El timeout de resolución debe ser positivo.")
        if self.postcondition_timeout_seconds <= 0:
            raise ValueError("El timeout por intento debe ser positivo.")
        if self.final_postcondition_timeout_seconds <= 0:
            raise ValueError("El timeout final debe ser positivo.")


@dataclass(frozen=True, slots=True)
class VerifiedSelectionResult:
    attempt_count: int
    click_mode: ClickMode | None
    already_selected: bool = False


class VerifiedSelectionInteractor:
    """Selecciona resultados de búsqueda con reintento y postcondición.

    Es reutilizable por contratista, proyecto, supervisor y cualquier diálogo
    posterior que exponga un botón de selección y un valor verificable en el
    formulario de destino.
    """

    def __init__(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        timeout_seconds: float,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("El timeout debe ser mayor que cero.")
        self._driver = driver
        self._waits = waits
        self._resolver = resolver
        self._timeout_seconds = float(timeout_seconds)

    def select(
        self,
        *,
        trigger_key: str,
        postcondition: SelectionPostcondition,
        error_code: str,
        selection_label: str,
        policy: VerifiedSelectionPolicy | None = None,
    ) -> VerifiedSelectionResult:
        normalized_key = str(trigger_key).strip()
        normalized_code = str(error_code).strip()
        normalized_label = str(selection_label).strip()
        if not normalized_key:
            raise ValueError("La clave del botón de selección es obligatoria.")
        if not normalized_code:
            raise ValueError("El código de error es obligatorio.")
        if not normalized_label:
            raise ValueError("La etiqueta de selección es obligatoria.")

        active_policy = policy or VerifiedSelectionPolicy()
        if self._safe_postcondition(postcondition):
            return VerifiedSelectionResult(
                attempt_count=0,
                click_mode=None,
                already_selected=True,
            )

        attempts: list[dict[str, object]] = []
        resolve_timeout = min(
            active_policy.resolve_timeout_seconds,
            self._timeout_seconds,
        )
        postcondition_timeout = min(
            active_policy.postcondition_timeout_seconds,
            self._timeout_seconds,
        )

        for attempt_number, click_mode in enumerate(
            active_policy.click_modes,
            start=1,
        ):
            try:
                # Se vuelve a resolver en cada intento porque los DataGrid de
                # React pueden reemplazar la fila o el botón tras un clic.
                trigger = self._resolver.clickable(
                    normalized_key,
                    timeout_seconds=resolve_timeout,
                )
                self._scroll_into_view(trigger)
                self._perform_click(trigger, click_mode)
            except (PortalTimeoutError, WebDriverException) as error:
                attempts.append(
                    {
                        "attempt": attempt_number,
                        "mode": click_mode,
                        "outcome": type(error).__name__,
                    }
                )
                continue

            try:
                self._waits.until(
                    lambda driver: bool(postcondition(driver)),
                    timeout_seconds=postcondition_timeout,
                )
                return VerifiedSelectionResult(
                    attempt_count=attempt_number,
                    click_mode=click_mode,
                )
            except TimeoutException:
                attempts.append(
                    {
                        "attempt": attempt_number,
                        "mode": click_mode,
                        "outcome": "click_without_postcondition",
                    }
                )

        final_timeout = min(
            active_policy.final_postcondition_timeout_seconds,
            self._timeout_seconds,
        )
        try:
            self._waits.until(
                lambda driver: bool(postcondition(driver)),
                timeout_seconds=final_timeout,
            )
            return VerifiedSelectionResult(
                attempt_count=len(active_policy.click_modes),
                click_mode=active_policy.click_modes[-1],
            )
        except TimeoutException as error:
            raise PortalTimeoutError(
                "No fue posible confirmar la selección de "
                f"{normalized_label} después de varios intentos.",
                code=normalized_code,
                metadata={
                    "trigger_key": normalized_key,
                    "selection_label": normalized_label,
                    "attempt_count": len(active_policy.click_modes),
                    "attempts": attempts,
                },
            ) from error

    def _safe_postcondition(
        self,
        postcondition: SelectionPostcondition,
    ) -> bool:
        try:
            return bool(postcondition(self._driver))
        except Exception:
            return False

    def _scroll_into_view(self, element: WebElement) -> None:
        self._driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'center'});",
            element,
        )

    def _perform_click(
        self,
        element: WebElement,
        mode: ClickMode,
    ) -> None:
        if mode == "native":
            element.click()
            return
        if mode == "actions":
            ActionChains(self._driver).move_to_element(element).click().perform()
            return
        if mode == "javascript":
            self._driver.execute_script("arguments[0].click();", element)
            return
        raise ValueError(f"Modo de clic no soportado: {mode}.")
