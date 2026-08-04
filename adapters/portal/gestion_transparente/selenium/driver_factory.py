<<<<<<< HEAD
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver


class BrowserStartupError(RuntimeError):
    """No fue posible crear o configurar la sesión del navegador."""


class WebDriverFactory(Protocol):
    """Contrato mínimo requerido por BrowserSession."""

    def create(self) -> WebDriver:
        ...


@dataclass(frozen=True, slots=True)
class BrowserSettings:
    """
    Configuración de una sesión local de Google Chrome.

    Si `driver_path` es None, Selenium utilizará Selenium Manager.
    """

    headless: bool = False

    driver_path: Path | None = None
    chrome_binary: Path | None = None

    download_directory: Path | None = None
    user_data_directory: Path | None = None
    profile_directory: str | None = None

    page_load_timeout_seconds: float = 60.0
    script_timeout_seconds: float = 30.0

    window_width: int = 1440
    window_height: int = 900

    accept_insecure_certificates: bool = False
    disable_notifications: bool = True

    additional_arguments: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if self.page_load_timeout_seconds <= 0:
            raise ValueError(
                "El timeout de carga debe ser mayor que cero."
            )

        if self.script_timeout_seconds <= 0:
            raise ValueError(
                "El timeout de scripts debe ser mayor que cero."
            )

        if self.window_width <= 0:
            raise ValueError(
                "El ancho de la ventana debe ser mayor que cero."
            )

        if self.window_height <= 0:
            raise ValueError(
                "La altura de la ventana debe ser mayor que cero."
            )

        if self.driver_path is not None:
            object.__setattr__(
                self,
                "driver_path",
                Path(self.driver_path),
            )

        if self.chrome_binary is not None:
            object.__setattr__(
                self,
                "chrome_binary",
                Path(self.chrome_binary),
            )

        if self.download_directory is not None:
            object.__setattr__(
                self,
                "download_directory",
                Path(self.download_directory),
            )

        if self.user_data_directory is not None:
            object.__setattr__(
                self,
                "user_data_directory",
                Path(self.user_data_directory),
            )


class DriverFactory:
    """
    Construye el WebDriver configurado para Gestión Transparente.

    No contiene navegación, login ni lógica del portal.
    """

    def __init__(
        self,
        settings: BrowserSettings | None = None,
    ) -> None:
        self._settings = settings or BrowserSettings()

    @property
    def settings(self) -> BrowserSettings:
        return self._settings

    def create(self) -> WebDriver:
        options = self._build_options()
        driver: WebDriver | None = None

        try:
            if self._settings.driver_path is None:
                # Selenium Manager resolverá ChromeDriver.
                driver = webdriver.Chrome(
                    options=options
                )
            else:
                driver_path = (
                    self._settings.driver_path
                )

                if not driver_path.is_file():
                    raise BrowserStartupError(
                        "No existe el ejecutable de ChromeDriver: "
                        f"'{driver_path}'."
                    )

                service = Service(
                    executable_path=str(driver_path)
                )

                driver = webdriver.Chrome(
                    service=service,
                    options=options,
                )

            driver.set_page_load_timeout(
                self._settings.page_load_timeout_seconds
            )

            driver.set_script_timeout(
                self._settings.script_timeout_seconds
            )

            # No mezclar implicit waits con WebDriverWait.
            driver.implicitly_wait(0)

            return driver

        except BrowserStartupError:
            if driver is not None:
                self._safe_quit(driver)

            raise

        except WebDriverException as error:
            if driver is not None:
                self._safe_quit(driver)

            raise BrowserStartupError(
                "No fue posible iniciar Google Chrome mediante "
                f"Selenium: {error}"
            ) from error

        except Exception:
            if driver is not None:
                self._safe_quit(driver)

            raise

    def _build_options(self) -> Options:
        settings = self._settings
        options = Options()

        options.accept_insecure_certs = (
            settings.accept_insecure_certificates
        )

        if settings.chrome_binary is not None:
            options.binary_location = str(
                settings.chrome_binary
            )

        if settings.headless:
            options.add_argument("--headless=new")

        options.add_argument(
            f"--window-size="
            f"{settings.window_width},"
            f"{settings.window_height}"
        )

        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-infobars")

        if settings.disable_notifications:
            options.add_argument(
                "--disable-notifications"
            )

        if settings.user_data_directory is not None:
            options.add_argument(
                "--user-data-dir="
                f"{settings.user_data_directory.resolve()}"
            )

        if settings.profile_directory:
            options.add_argument(
                "--profile-directory="
                f"{settings.profile_directory.strip()}"
            )

        for argument in settings.additional_arguments:
            normalized = str(argument).strip()

            if normalized:
                options.add_argument(normalized)

        if settings.download_directory is not None:
            download_directory = (
                settings.download_directory.resolve()
            )

            download_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            options.add_experimental_option(
                "prefs",
                {
                    "download.default_directory": str(
                        download_directory
                    ),
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True,
                },
            )

        return options

    @staticmethod
    def _safe_quit(driver: WebDriver) -> None:
        try:
            driver.quit()
        except Exception:
=======
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver


class BrowserStartupError(RuntimeError):
    """No fue posible crear o configurar la sesión del navegador."""


class WebDriverFactory(Protocol):
    """Contrato mínimo requerido por BrowserSession."""

    def create(self) -> WebDriver:
        ...


@dataclass(frozen=True, slots=True)
class BrowserSettings:
    """
    Configuración de una sesión local de Google Chrome.

    Si `driver_path` es None, Selenium utilizará Selenium Manager.
    """

    headless: bool = False

    driver_path: Path | None = None
    chrome_binary: Path | None = None

    download_directory: Path | None = None
    user_data_directory: Path | None = None
    profile_directory: str | None = None

    page_load_timeout_seconds: float = 60.0
    script_timeout_seconds: float = 30.0

    window_width: int = 1440
    window_height: int = 900

    accept_insecure_certificates: bool = False
    disable_notifications: bool = True

    additional_arguments: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if self.page_load_timeout_seconds <= 0:
            raise ValueError(
                "El timeout de carga debe ser mayor que cero."
            )

        if self.script_timeout_seconds <= 0:
            raise ValueError(
                "El timeout de scripts debe ser mayor que cero."
            )

        if self.window_width <= 0:
            raise ValueError(
                "El ancho de la ventana debe ser mayor que cero."
            )

        if self.window_height <= 0:
            raise ValueError(
                "La altura de la ventana debe ser mayor que cero."
            )

        if self.driver_path is not None:
            object.__setattr__(
                self,
                "driver_path",
                Path(self.driver_path),
            )

        if self.chrome_binary is not None:
            object.__setattr__(
                self,
                "chrome_binary",
                Path(self.chrome_binary),
            )

        if self.download_directory is not None:
            object.__setattr__(
                self,
                "download_directory",
                Path(self.download_directory),
            )

        if self.user_data_directory is not None:
            object.__setattr__(
                self,
                "user_data_directory",
                Path(self.user_data_directory),
            )


class DriverFactory:
    """
    Construye el WebDriver configurado para Gestión Transparente.

    No contiene navegación, login ni lógica del portal.
    """

    def __init__(
        self,
        settings: BrowserSettings | None = None,
    ) -> None:
        self._settings = settings or BrowserSettings()

    @property
    def settings(self) -> BrowserSettings:
        return self._settings

    def create(self) -> WebDriver:
        options = self._build_options()
        driver: WebDriver | None = None

        try:
            if self._settings.driver_path is None:
                # Selenium Manager resolverá ChromeDriver.
                driver = webdriver.Chrome(
                    options=options
                )
            else:
                driver_path = (
                    self._settings.driver_path
                )

                if not driver_path.is_file():
                    raise BrowserStartupError(
                        "No existe el ejecutable de ChromeDriver: "
                        f"'{driver_path}'."
                    )

                service = Service(
                    executable_path=str(driver_path)
                )

                driver = webdriver.Chrome(
                    service=service,
                    options=options,
                )

            driver.set_page_load_timeout(
                self._settings.page_load_timeout_seconds
            )

            driver.set_script_timeout(
                self._settings.script_timeout_seconds
            )

            # No mezclar implicit waits con WebDriverWait.
            driver.implicitly_wait(0)

            return driver

        except BrowserStartupError:
            if driver is not None:
                self._safe_quit(driver)

            raise

        except WebDriverException as error:
            if driver is not None:
                self._safe_quit(driver)

            raise BrowserStartupError(
                "No fue posible iniciar Google Chrome mediante "
                f"Selenium: {error}"
            ) from error

        except Exception:
            if driver is not None:
                self._safe_quit(driver)

            raise

    def _build_options(self) -> Options:
        settings = self._settings
        options = Options()

        options.accept_insecure_certs = (
            settings.accept_insecure_certificates
        )

        if settings.chrome_binary is not None:
            options.binary_location = str(
                settings.chrome_binary
            )

        if settings.headless:
            options.add_argument("--headless=new")

        options.add_argument(
            f"--window-size="
            f"{settings.window_width},"
            f"{settings.window_height}"
        )

        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-infobars")

        if settings.disable_notifications:
            options.add_argument(
                "--disable-notifications"
            )

        if settings.user_data_directory is not None:
            options.add_argument(
                "--user-data-dir="
                f"{settings.user_data_directory.resolve()}"
            )

        if settings.profile_directory:
            options.add_argument(
                "--profile-directory="
                f"{settings.profile_directory.strip()}"
            )

        for argument in settings.additional_arguments:
            normalized = str(argument).strip()

            if normalized:
                options.add_argument(normalized)

        if settings.download_directory is not None:
            download_directory = (
                settings.download_directory.resolve()
            )

            download_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            options.add_experimental_option(
                "prefs",
                {
                    "download.default_directory": str(
                        download_directory
                    ),
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True,
                },
            )

        return options

    @staticmethod
    def _safe_quit(driver: WebDriver) -> None:
        try:
            driver.quit()
        except Exception:
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
            pass