from __future__ import annotations

from types import TracebackType
from typing import Self

from selenium.webdriver.remote.webdriver import WebDriver

from adapters.portal.gestion_transparente.selenium.driver_factory import (
    WebDriverFactory,
)


class BrowserSessionError(RuntimeError):
    """Error relacionado con el ciclo de vida del navegador."""


class BrowserSessionNotStartedError(
    BrowserSessionError
):
    """Se intentó usar el navegador antes de abrir la sesión."""


class BrowserSession:
    """
    Controla el ciclo de vida de una única instancia WebDriver.

    Puede utilizarse manualmente:

        session.open()
        session.navigate(url)
        session.close()

    O como context manager:

        with BrowserSession(factory) as session:
            session.navigate(url)
    """

    def __init__(
        self,
        factory: WebDriverFactory,
    ) -> None:
        self._factory = factory
        self._driver: WebDriver | None = None

    @property
    def is_open(self) -> bool:
        return self._driver is not None

    @property
    def driver(self) -> WebDriver:
        if self._driver is None:
            raise BrowserSessionNotStartedError(
                "La sesión del navegador no ha sido iniciada."
            )

        return self._driver

    def open(self) -> WebDriver:
        """
        Abre la sesión de forma idempotente.

        Si ya existe una sesión, devuelve el mismo driver.
        """

        if self._driver is None:
            self._driver = self._factory.create()

        return self._driver

    def navigate(self, url: str) -> None:
        normalized_url = str(url).strip()

        if not normalized_url:
            raise ValueError(
                "La URL de navegación es obligatoria."
            )

        self.driver.get(normalized_url)

    def refresh(self) -> None:
        self.driver.refresh()

    def maximize(self) -> None:
        self.driver.maximize_window()

    def close(self) -> None:
        """
        Cierra la sesión de forma idempotente.
        """

        driver = self._driver
        self._driver = None

        if driver is None:
            return

        try:
            driver.quit()
        except Exception as error:
            raise BrowserSessionError(
                "Se produjo un error al cerrar el navegador: "
                f"{error}"
            ) from error

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            self.close()
        except BrowserSessionError:
            # Un fallo de quit no debe ocultar la causa que interrumpió
            # la automatización. Sin excepción previa, sí se propaga.
            if exception is None:
                raise

        # No suprime la excepción original.
        return False