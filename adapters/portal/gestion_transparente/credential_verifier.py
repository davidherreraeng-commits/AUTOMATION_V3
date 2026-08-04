from __future__ import annotations

from pathlib import Path
from threading import Lock

from application.ports.portal_credential_verifier import (
    PortalCredentialVerificationResult,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)
from adapters.portal.gestion_transparente.selenium.browser_session import (
    BrowserSession,
)
from adapters.portal.gestion_transparente.selenium.driver_factory import (
    BrowserSettings,
    BrowserStartupError,
    DriverFactory,
)
from adapters.portal.gestion_transparente.selenium.element_resolver import (
    ElementResolver,
)
from adapters.portal.gestion_transparente.selenium.waits import SeleniumWaits
from domain.errors import PortalTimeoutError


class SeleniumPortalCredentialVerifier:
    """Prueba credenciales GT en una sesión aislada de Chrome."""

    def __init__(
        self,
        *,
        login_url: str,
        headless: bool = False,
        timeout_seconds: float = 25.0,
        driver_path: Path | None = None,
        chrome_binary: Path | None = None,
    ) -> None:
        normalized_url = str(login_url).strip()
        if not normalized_url:
            raise ValueError("La URL de inicio de sesión es obligatoria.")
        if timeout_seconds <= 0:
            raise ValueError("El timeout debe ser mayor que cero.")

        self._login_url = normalized_url
        self._timeout_seconds = float(timeout_seconds)
        self._factory = DriverFactory(
            BrowserSettings(
                headless=bool(headless),
                driver_path=driver_path,
                chrome_binary=chrome_binary,
                page_load_timeout_seconds=max(60.0, timeout_seconds * 2),
                script_timeout_seconds=max(30.0, timeout_seconds),
                additional_arguments=(
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    "--disable-gpu",
                ),
            )
        )
        self._lock = Lock()

    def verify(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ) -> PortalCredentialVerificationResult:
        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return PortalCredentialVerificationResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )

        if not self._lock.acquire(blocking=False):
            return PortalCredentialVerificationResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya hay una comprobación de credenciales en curso. "
                    "Espere unos segundos e intente nuevamente."
                ),
            )

        try:
            return self._verify_in_browser(username, password)
        finally:
            self._lock.release()

    def _verify_in_browser(
        self,
        username: str,
        password: str,
    ) -> PortalCredentialVerificationResult:
        try:
            with BrowserSession(self._factory) as session:
                session.navigate(self._login_url)
                waits = SeleniumWaits(
                    session.driver,
                    default_timeout_seconds=self._timeout_seconds,
                )
                resolver = ElementResolver(
                    registry=build_registry(),
                    waits=waits,
                    diagnostics=None,
                )

                username_input = resolver.visible(
                    "portal.login.username",
                    timeout_seconds=self._timeout_seconds,
                )
                password_input = resolver.visible(
                    "portal.login.password",
                    timeout_seconds=self._timeout_seconds,
                )
                submit = resolver.clickable(
                    "portal.login.submit",
                    timeout_seconds=self._timeout_seconds,
                )

                username_input.clear()
                username_input.send_keys(username)
                password_input.clear()
                password_input.send_keys(password)
                submit.click()

                try:
                    resolver.visible(
                        "navigation.contracting_menu",
                        timeout_seconds=self._timeout_seconds,
                    )
                    return PortalCredentialVerificationResult(
                        success=True,
                        code="AUTHENTICATED",
                        message=(
                            "Las credenciales fueron validadas correctamente "
                            "en Gestión Transparente."
                        ),
                    )
                except PortalTimeoutError:
                    login_still_visible = resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    )
                    if login_still_visible is not None:
                        return PortalCredentialVerificationResult(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o "
                                "la contraseña."
                            ),
                        )
                    return PortalCredentialVerificationResult(
                        success=False,
                        code="UNEXPECTED_PORTAL_STATE",
                        message=(
                            "El portal respondió, pero no fue posible confirmar "
                            "el inicio de sesión. Se requiere revisión técnica."
                        ),
                    )

        except BrowserStartupError:
            return PortalCredentialVerificationResult(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message=(
                    "No fue posible iniciar Google Chrome para probar las "
                    "credenciales."
                ),
            )
        except PortalTimeoutError:
            return PortalCredentialVerificationResult(
                success=False,
                code="PORTAL_UNAVAILABLE",
                message=(
                    "Gestión Transparente no respondió dentro del tiempo "
                    "esperado."
                ),
            )
        except Exception:
            return PortalCredentialVerificationResult(
                success=False,
                code="VERIFICATION_ERROR",
                message=(
                    "Ocurrió un error al comprobar las credenciales. "
                    "No se almacenó ni se mostró la contraseña."
                ),
            )
