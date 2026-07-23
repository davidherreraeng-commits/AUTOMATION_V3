from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import (
    expected_conditions as EC,
)
from selenium.webdriver.support.ui import WebDriverWait


Locator = tuple[str, str]
T = TypeVar("T")


class SeleniumWaits:
    """
    Fachada centralizada para las esperas explícitas de Selenium.

    Evita que cada componente cree sus propios WebDriverWait con
    tiempos diferentes.
    """

    def __init__(
        self,
        driver: WebDriver,
        *,
        default_timeout_seconds: float = 15.0,
        poll_frequency_seconds: float = 0.25,
    ) -> None:
        if default_timeout_seconds <= 0:
            raise ValueError(
                "El timeout predeterminado debe ser mayor "
                "que cero."
            )

        if poll_frequency_seconds <= 0:
            raise ValueError(
                "La frecuencia de consulta debe ser mayor "
                "que cero."
            )

        self._driver = driver
        self._default_timeout_seconds = (
            default_timeout_seconds
        )
        self._poll_frequency_seconds = (
            poll_frequency_seconds
        )

    @property
    def default_timeout_seconds(self) -> float:
        return self._default_timeout_seconds

    @property
    def poll_frequency_seconds(self) -> float:
        return self._poll_frequency_seconds

    def presence(
        self,
        locator: Locator,
        *,
        timeout_seconds: float | None = None,
    ) -> WebElement:
        return self.until(
            EC.presence_of_element_located(locator),
            timeout_seconds=timeout_seconds,
        )

    def visible(
        self,
        locator: Locator,
        *,
        timeout_seconds: float | None = None,
    ) -> WebElement:
        return self.until(
            EC.visibility_of_element_located(locator),
            timeout_seconds=timeout_seconds,
        )

    def clickable(
        self,
        locator: Locator,
        *,
        timeout_seconds: float | None = None,
    ) -> WebElement:
        return self.until(
            EC.element_to_be_clickable(locator),
            timeout_seconds=timeout_seconds,
        )

    def invisible(
        self,
        locator: Locator,
        *,
        timeout_seconds: float | None = None,
    ) -> bool:
        return bool(
            self.until(
                EC.invisibility_of_element_located(
                    locator
                ),
                timeout_seconds=timeout_seconds,
            )
        )

    def url_contains(
        self,
        fragment: str,
        *,
        timeout_seconds: float | None = None,
    ) -> bool:
        normalized_fragment = str(fragment).strip()

        if not normalized_fragment:
            raise ValueError(
                "El fragmento de URL es obligatorio."
            )

        return bool(
            self.until(
                EC.url_contains(normalized_fragment),
                timeout_seconds=timeout_seconds,
            )
        )

    def staleness(
        self,
        element: WebElement,
        *,
        timeout_seconds: float | None = None,
    ) -> bool:
        return bool(
            self.until(
                EC.staleness_of(element),
                timeout_seconds=timeout_seconds,
            )
        )

    def until(
        self,
        condition: Callable[[WebDriver], T | Any],
        *,
        timeout_seconds: float | None = None,
        message: str = "",
    ) -> T:
        timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else self._default_timeout_seconds
        )

        if timeout <= 0:
            raise ValueError(
                "El timeout debe ser mayor que cero."
            )

        wait = WebDriverWait(
            self._driver,
            timeout,
            poll_frequency=self._poll_frequency_seconds,
        )

        return wait.until(
            condition,
            message=message,
        )