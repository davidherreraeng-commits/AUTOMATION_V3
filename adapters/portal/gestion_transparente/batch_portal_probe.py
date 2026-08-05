from __future__ import annotations

from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re
import unicodedata
from threading import Lock
from time import monotonic

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from application.ports.batch_portal_probe import (
    BatchAssistantProbeResult,
    BatchContractSaveProbeResult,
    BatchContractAvailabilityLinkProbeResult,
    BatchContractBudgetRegisterLinkProbeResult,
    BatchContractAdditionalDatesLinkProbeResult,
    BatchContractSupervisorLinkProbeResult,
    BatchGeneralCompletionDraftProbeResult,
    BatchGeneralDataDraftProbeResult,
    BatchGeneralValidationProbeResult,
    BatchHeaderDraftProbeResult,
    BatchHeaderValidationProbeResult,
    BatchPortalProbeResult,
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
    WebDriverFactory,
)
from adapters.portal.gestion_transparente.selenium.element_resolver import (
    ElementResolver,
)
from adapters.portal.gestion_transparente.selenium.waits import SeleniumWaits
from adapters.portal.gestion_transparente.selenium.verified_selection import (
    VerifiedSelectionInteractor,
)
from domain.enums.contractor_nature import ContractorNature
from domain.errors import PortalTimeoutError
from domain.models.contract import ContractData


class SeleniumBatchPortalProbe:
    """Valida navegación y ejecuta operaciones contractuales controladas.

    La navegación lateral de Gestión Transparente conserva su estado entre
    cargas y puede iniciar con los menús ya desplegados. Por eso este probe
    comprueba primero la visibilidad del siguiente nivel y solo pulsa el
    menú cuando realmente está cerrado.
    """

    _HEADER_CONTROL_SPECS: tuple[
        tuple[str, str, str, str],
        ...
    ] = (
        (
            "record_type_found",
            "contract.header.record_type_contract",
            "presence",
            "Tipo de registro Contrato",
        ),
        (
            "contract_number_found",
            "contract.header.contract_number",
            "visible",
            "Número del contrato",
        ),
        (
            "contractor_search_found",
            "contract.header.contractor_link",
            "clickable",
            "Búsqueda de contratista",
        ),
        (
            "project_search_found",
            "contract.header.project_link",
            "clickable",
            "Búsqueda de proyecto",
        ),
        (
            "validate_button_found",
            "contract.header.validate_button",
            "clickable",
            "Botón Validar",
        ),
    )

    _GENERAL_CORE_CONTROL_SPECS: tuple[
        tuple[str, str, str],
        ...
    ] = (
        (
            "general_object_found",
            "general.object_description",
            "Objeto del contrato",
        ),
        (
            "general_signing_date_found",
            "general.signing_date",
            "Fecha de suscripción",
        ),
        (
            "general_starting_date_found",
            "general.starting_date",
            "Fecha de inicio",
        ),
        (
            "general_amount_found",
            "general.amount",
            "Valor contractual",
        ),
        (
            "general_contract_term_found",
            "general.contract_term",
            "Plazo estimado",
        ),
    )

    _DEFAULT_EXECUTION_DEPARTMENT = "Antioquia"
    _DEFAULT_EXECUTION_CITY = "Medellín"

    def __init__(
        self,
        *,
        login_url: str,
        headless: bool = False,
        timeout_seconds: float = 25.0,
        driver_path: Path | None = None,
        chrome_binary: Path | None = None,
        factory: WebDriverFactory | None = None,
    ) -> None:
        normalized_url = str(login_url).strip()
        if not normalized_url:
            raise ValueError("La URL de inicio de sesión es obligatoria.")
        if timeout_seconds <= 0:
            raise ValueError("El timeout debe ser mayor que cero.")

        self._login_url = normalized_url
        self._timeout_seconds = float(timeout_seconds)
        self._factory = factory or DriverFactory(
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

    @property
    def name(self) -> str:
        return "selenium-gt-navigation-probe-v2026_07-state-aware"

    def probe(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ) -> BatchPortalProbeResult:
        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchPortalProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchPortalProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación de navegación en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_in_browser(
                username=username,
                password=password,
                started=started,
            )
        finally:
            self._lock.release()

    def probe_assistant_form(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ) -> BatchAssistantProbeResult:
        """Abre el asistente, selecciona Contrato y comprueba C1-C2."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchAssistantProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchAssistantProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_assistant_form_in_browser(
                username=username,
                password=password,
                started=started,
            )
        finally:
            self._lock.release()

    def probe_header_draft(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchHeaderDraftProbeResult:
        """Completa C1-C2 con un contrato sin pulsar Validar."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchHeaderDraftProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchHeaderDraftProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato de diagnóstico no es válido.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchHeaderDraftProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_header_draft_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()


    def probe_header_validation(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchHeaderValidationProbeResult:
        """Valida C1-C2 y comprueba C3 sin completar ni guardar datos."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchHeaderValidationProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchHeaderValidationProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato de diagnóstico no es válido.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchHeaderValidationProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_header_validation_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()

    def probe_general_data_draft(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchGeneralDataDraftProbeResult:
        """Completa C3 sin pulsar la validación general ni Guardar."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchGeneralDataDraftProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchGeneralDataDraftProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato de diagnóstico no es válido.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchGeneralDataDraftProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_general_data_draft_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()


    def probe_general_completion_draft(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchGeneralCompletionDraftProbeResult:
        """Completa C3-C4 sin pulsar la validación general ni Guardar."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchGeneralCompletionDraftProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchGeneralCompletionDraftProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato de diagnóstico no es válido.",
            )
        if not str(contract.secop_url or "").strip():
            return BatchGeneralCompletionDraftProbeResult(
                success=False,
                code="MISSING_SECOP_URL",
                message=(
                    "La carga C4 requiere el enlace obligatorio del proceso "
                    "publicado en SECOP II."
                ),
            )

        if not self._lock.acquire(blocking=False):
            return BatchGeneralCompletionDraftProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_general_completion_draft_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()


    def probe_general_validation(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchGeneralValidationProbeResult:
        """Valida C3-C4 y confirma Guardar sin pulsarlo."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchGeneralValidationProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchGeneralValidationProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato de diagnóstico no es válido.",
            )
        if not str(contract.secop_url or "").strip():
            return BatchGeneralValidationProbeResult(
                success=False,
                code="MISSING_SECOP_URL",
                message=(
                    "La validación general requiere el enlace obligatorio "
                    "del proceso publicado en SECOP II."
                ),
            )

        if not self._lock.acquire(blocking=False):
            return BatchGeneralValidationProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_general_validation_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()


    def probe_contract_save(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractSaveProbeResult:
        """Guarda un contrato autorizado y confirma la siguiente etapa."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchContractSaveProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchContractSaveProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato autorizado no es válido.",
            )
        if not str(contract.secop_url or "").strip():
            return BatchContractSaveProbeResult(
                success=False,
                code="MISSING_SECOP_URL",
                message=(
                    "El guardado requiere el enlace obligatorio "
                    "del proceso publicado en SECOP II."
                ),
            )

        if not self._lock.acquire(blocking=False):
            return BatchContractSaveProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_contract_save_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()

    def probe_contract_supervisor_link(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractSupervisorLinkProbeResult:
        """Guarda un contrato autorizado y vincula su supervisor interno."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchContractSupervisorLinkProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchContractSupervisorLinkProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato autorizado no es válido.",
            )
        if not str(contract.secop_url or "").strip():
            return BatchContractSupervisorLinkProbeResult(
                success=False,
                code="MISSING_SECOP_URL",
                message=(
                    "El guardado requiere el enlace obligatorio "
                    "del proceso publicado en SECOP II."
                ),
            )
        if not str(contract.supervisor.document_number).strip():
            return BatchContractSupervisorLinkProbeResult(
                success=False,
                code="MISSING_SUPERVISOR_DOCUMENT",
                message="La cédula del supervisor es obligatoria.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchContractSupervisorLinkProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_contract_supervisor_link_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()


    def probe_contract_availability_link(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractAvailabilityLinkProbeResult:
        """Guarda contrato, vincula supervisor y vincula el CDP."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchContractAvailabilityLinkProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchContractAvailabilityLinkProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato autorizado no es válido.",
            )
        if not str(contract.secop_url or "").strip():
            return BatchContractAvailabilityLinkProbeResult(
                success=False,
                code="MISSING_SECOP_URL",
                message=(
                    "El guardado requiere el enlace obligatorio "
                    "del proceso publicado en SECOP II."
                ),
            )
        if not str(contract.supervisor.document_number).strip():
            return BatchContractAvailabilityLinkProbeResult(
                success=False,
                code="MISSING_SUPERVISOR_DOCUMENT",
                message="La cédula del supervisor es obligatoria.",
            )
        if not str(contract.budget.cdp_code).strip():
            return BatchContractAvailabilityLinkProbeResult(
                success=False,
                code="MISSING_CDP_CODE",
                message="El número de CDP es obligatorio.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchContractAvailabilityLinkProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_contract_availability_link_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()


    def probe_contract_budget_register_link(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractBudgetRegisterLinkProbeResult:
        """Guarda contrato y vincula supervisor, CDP y registro presupuestal."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchContractBudgetRegisterLinkProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchContractBudgetRegisterLinkProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato autorizado no es válido.",
            )
        if not str(contract.secop_url or "").strip():
            return BatchContractBudgetRegisterLinkProbeResult(
                success=False,
                code="MISSING_SECOP_URL",
                message=(
                    "El guardado requiere el enlace obligatorio "
                    "del proceso publicado en SECOP II."
                ),
            )
        if not str(contract.supervisor.document_number).strip():
            return BatchContractBudgetRegisterLinkProbeResult(
                success=False,
                code="MISSING_SUPERVISOR_DOCUMENT",
                message="La cédula del supervisor es obligatoria.",
            )
        if not str(contract.budget.cdp_code).strip():
            return BatchContractBudgetRegisterLinkProbeResult(
                success=False,
                code="MISSING_CDP_CODE",
                message="El número de CDP es obligatorio.",
            )
        if not str(contract.budget.budget_register_number or "").strip():
            return BatchContractBudgetRegisterLinkProbeResult(
                success=False,
                code="MISSING_BUDGET_REGISTER_NUMBER",
                message="El número de registro presupuestal es obligatorio.",
            )
        if contract.budget.gross_total <= Decimal("0"):
            return BatchContractBudgetRegisterLinkProbeResult(
                success=False,
                code="INVALID_GROSS_TOTAL",
                message="El Total Bruto debe ser mayor que cero.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchContractBudgetRegisterLinkProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_contract_budget_register_link_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()


    def probe_contract_additional_dates_link(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractAdditionalDatesLinkProbeResult:
        """Guarda el contrato y vincula C6-C9 de forma controlada."""

        username = str(portal_username).strip()
        password = str(portal_password)
        if not username or not password:
            return BatchContractAdditionalDatesLinkProbeResult(
                success=False,
                code="INVALID_INPUT",
                message="El usuario y la contraseña del portal son obligatorios.",
            )
        if not isinstance(contract, ContractData):
            return BatchContractAdditionalDatesLinkProbeResult(
                success=False,
                code="INVALID_CONTRACT",
                message="El contrato autorizado no es válido.",
            )
        if not str(contract.secop_url or "").strip():
            return BatchContractAdditionalDatesLinkProbeResult(
                success=False,
                code="MISSING_SECOP_URL",
                message=(
                    "El guardado requiere el enlace obligatorio "
                    "del proceso publicado en SECOP II."
                ),
            )
        if not str(contract.supervisor.document_number).strip():
            return BatchContractAdditionalDatesLinkProbeResult(
                success=False,
                code="MISSING_SUPERVISOR_DOCUMENT",
                message="La cédula del supervisor es obligatoria.",
            )
        if not str(contract.budget.cdp_code).strip():
            return BatchContractAdditionalDatesLinkProbeResult(
                success=False,
                code="MISSING_CDP_CODE",
                message="El número de CDP es obligatorio.",
            )
        if not str(contract.budget.budget_register_number or "").strip():
            return BatchContractAdditionalDatesLinkProbeResult(
                success=False,
                code="MISSING_BUDGET_REGISTER_NUMBER",
                message="El número de registro presupuestal es obligatorio.",
            )
        if contract.budget.gross_total <= Decimal("0"):
            return BatchContractAdditionalDatesLinkProbeResult(
                success=False,
                code="INVALID_GROSS_TOTAL",
                message="El Total Bruto debe ser mayor que cero.",
            )

        if not self._lock.acquire(blocking=False):
            return BatchContractAdditionalDatesLinkProbeResult(
                success=False,
                code="BROWSER_BUSY",
                message=(
                    "Ya existe una comprobación del portal en curso para "
                    "este proceso."
                ),
            )

        started = monotonic()
        try:
            return self._probe_contract_additional_dates_link_in_browser(
                username=username,
                password=password,
                contract=contract,
                started=started,
            )
        finally:
            self._lock.release()



    def _probe_in_browser(
        self,
        *,
        username: str,
        password: str,
        started: float,
    ) -> BatchPortalProbeResult:
        authenticated = False
        contracting_menu_found = False
        enter_contract_found = False
        assistant_access_found = False

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchPortalProbeResult:
            return BatchPortalProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                contracting_menu_found=contracting_menu_found,
                enter_contract_found=enter_contract_found,
                assistant_access_found=assistant_access_found,
                duration_ms=max(0, round((monotonic() - started) * 1000)),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña."
                            ),
                        )
                    return result(
                        success=False,
                        code="AUTHENTICATED_STATE_UNCONFIRMED",
                        message=(
                            "El portal respondió, pero no fue posible confirmar "
                            "el menú de Contratación."
                        ),
                    )

                authenticated = True
                contracting_menu_found = True

                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                enter_contract_found = True

                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                assistant_access_found = True

                return result(
                    success=True,
                    code="NAVIGATION_READY",
                    message=(
                        "Se confirmó el login y la ruta hasta el acceso al "
                        "Asistente de Contratación. El formulario no fue "
                        "abierto y no se modificó información."
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            code = (
                error.code
                if error.code != "PORTAL_TIMEOUT"
                else "PORTAL_NAVIGATION_TIMEOUT"
            )
            return result(
                success=False,
                code=code,
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="PROBE_ERROR",
                message=(
                    "La comprobación terminó con un error controlado: "
                    f"{type(error).__name__}."
                ),
            )

    def _probe_assistant_form_in_browser(
        self,
        *,
        username: str,
        password: str,
        started: float,
    ) -> BatchAssistantProbeResult:
        authenticated = False
        assistant_opened = False
        assistant_container_found = False
        flags = {
            "record_type_found": False,
            "contract_number_found": False,
            "contractor_search_found": False,
            "project_search_found": False,
            "validate_button_found": False,
        }
        missing_controls: tuple[str, ...] = ()

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchAssistantProbeResult:
            return BatchAssistantProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                assistant_container_found=assistant_container_found,
                record_type_found=flags["record_type_found"],
                contract_number_found=flags["contract_number_found"],
                contractor_search_found=flags["contractor_search_found"],
                project_search_found=flags["project_search_found"],
                validate_button_found=flags["validate_button_found"],
                missing_controls=missing_controls,
                duration_ms=max(0, round((monotonic() - started) * 1000)),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña."
                            ),
                        )
                    return result(
                        success=False,
                        code="AUTHENTICATED_STATE_UNCONFIRMED",
                        message=(
                            "El portal respondió, pero no fue posible confirmar "
                            "el estado autenticado."
                        ),
                    )

                authenticated = True

                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True
                assistant_container_found = True

                # El portal solo renderiza Número, Contratista, Proyecto y
                # Validar después de seleccionar explícitamente el tipo de
                # registro Contrato. El clic es idempotente para un radio y
                # no persiste información contractual.
                self._select_contract_record_type(
                    driver=session.driver,
                    resolver=resolver,
                )

                flags, missing_controls = self._inspect_header_controls(
                    resolver
                )
                if missing_controls:
                    return result(
                        success=False,
                        code="ASSISTANT_FORM_INCOMPLETE",
                        message=(
                            "El Asistente de Contratación abrió, pero faltan "
                            "controles esperados de C1-C2: "
                            + ", ".join(missing_controls)
                            + "."
                        ),
                    )

                return result(
                    success=True,
                    code="ASSISTANT_FORM_READY",
                    message=(
                        "Se abrió el Asistente de Contratación, se seleccionó "
                        "el tipo de registro Contrato y se confirmaron los "
                        "controles C1-C2. No se ingresaron datos, no se pulsó "
                        "Validar y no se guardó información."
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            code = (
                error.code
                if error.code != "PORTAL_TIMEOUT"
                else "ASSISTANT_FORM_TIMEOUT"
            )
            return result(
                success=False,
                code=code,
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="ASSISTANT_PROBE_ERROR",
                message=(
                    "El diagnóstico C1-C2 terminó con un error controlado: "
                    f"{type(error).__name__}."
                ),
            )

    def _probe_header_draft_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchHeaderDraftProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "record_type_selected": False,
            "contract_number_written": False,
            "contractor_dialog_opened": False,
            "contractor_nature_selected": False,
            "contractor_document_written": False,
            "contractor_result_found": False,
            "contractor_selected": False,
            "project_dialog_opened": False,
            "project_code_written": False,
            "project_result_found": False,
            "project_selected": False,
            "validate_button_found": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchHeaderDraftProbeResult:
            return BatchHeaderDraftProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                record_type_selected=flags["record_type_selected"],
                contract_number_written=flags["contract_number_written"],
                contractor_dialog_opened=flags["contractor_dialog_opened"],
                contractor_nature_selected=flags["contractor_nature_selected"],
                contractor_document_written=flags["contractor_document_written"],
                contractor_result_found=flags["contractor_result_found"],
                contractor_selected=flags["contractor_selected"],
                project_dialog_opened=flags["project_dialog_opened"],
                project_code_written=flags["project_code_written"],
                project_result_found=flags["project_result_found"],
                project_selected=flags["project_selected"],
                validate_button_found=flags["validate_button_found"],
                validate_clicked=False,
                duration_ms=max(0, round((monotonic() - started) * 1000)),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña."
                            ),
                        )
                    return result(
                        success=False,
                        code="AUTHENTICATED_STATE_UNCONFIRMED",
                        message=(
                            "El portal respondió, pero no fue posible confirmar "
                            "el estado autenticado."
                        ),
                    )

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True
                flags.update(
                    self._populate_header_draft(
                        driver=session.driver,
                        waits=waits,
                        resolver=resolver,
                        contract=contract,
                    )
                )

                return result(
                    success=True,
                    code="HEADER_DRAFT_READY",
                    message=(
                        "Se completó el encabezado C1-C2 con un contrato del "
                        "lote. No se pulsó Validar y no se guardó información."
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "HEADER_DRAFT_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="HEADER_DRAFT_ERROR",
                message=(
                    "La carga diagnóstica C1-C2 terminó con un error "
                    f"controlado: {type(error).__name__}."
                ),
            )


    def _probe_header_validation_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchHeaderValidationProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "record_type_selected": False,
            "contract_number_written": False,
            "contractor_selected": False,
            "project_selected": False,
            "validate_button_found": False,
            "validate_clicked": False,
            "header_validation_confirmed": False,
            "general_data_ready": False,
            "general_object_found": False,
            "general_signing_date_found": False,
            "general_starting_date_found": False,
            "general_amount_found": False,
            "general_contract_term_found": False,
        }
        missing_controls: tuple[str, ...] = ()

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchHeaderValidationProbeResult:
            return BatchHeaderValidationProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                record_type_selected=flags["record_type_selected"],
                contract_number_written=flags["contract_number_written"],
                contractor_selected=flags["contractor_selected"],
                project_selected=flags["project_selected"],
                validate_button_found=flags["validate_button_found"],
                validate_clicked=flags["validate_clicked"],
                header_validation_confirmed=flags[
                    "header_validation_confirmed"
                ],
                general_data_ready=flags["general_data_ready"],
                general_object_found=flags["general_object_found"],
                general_signing_date_found=flags[
                    "general_signing_date_found"
                ],
                general_starting_date_found=flags[
                    "general_starting_date_found"
                ],
                general_amount_found=flags["general_amount_found"],
                general_contract_term_found=flags[
                    "general_contract_term_found"
                ],
                missing_controls=missing_controls,
                save_clicked=False,
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña."
                            ),
                        )
                    return result(
                        success=False,
                        code="AUTHENTICATED_STATE_UNCONFIRMED",
                        message=(
                            "El portal respondió, pero no fue posible "
                            "confirmar el estado autenticado."
                        ),
                    )

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                draft_flags = self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                for flag_name in (
                    "record_type_selected",
                    "contract_number_written",
                    "contractor_selected",
                    "project_selected",
                    "validate_button_found",
                ):
                    flags[flag_name] = draft_flags[flag_name]

                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )
                flags["validate_clicked"] = True
                flags["header_validation_confirmed"] = True

                general_flags, missing_controls = (
                    self._inspect_general_core_controls(resolver)
                )
                flags.update(general_flags)
                flags["general_data_ready"] = not missing_controls

                if missing_controls:
                    return result(
                        success=False,
                        code="GENERAL_FORM_INCOMPLETE",
                        message=(
                            "El encabezado C1-C2 fue validado, pero faltan "
                            "controles principales de C3: "
                            + ", ".join(missing_controls)
                            + "."
                        ),
                    )

                return result(
                    success=True,
                    code="HEADER_VALIDATION_READY",
                    message=(
                        "El encabezado C1-C2 fue validado y se confirmó la "
                        "apertura de los datos generales C3. No se completó "
                        "C3 y no se pulsó Guardar."
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "HEADER_VALIDATION_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="HEADER_VALIDATION_ERROR",
                message=(
                    "La validación diagnóstica de C1-C2 terminó con un "
                    f"error controlado: {type(error).__name__}."
                ),
            )

    def _probe_general_data_draft_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchGeneralDataDraftProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "header_validation_confirmed": False,
            "object_written": False,
            "signing_date_written": False,
            "starting_date_written": False,
            "amount_written": False,
            "amount_in_words_generated": False,
            "contract_term_written": False,
            "term_unit_days_selected": False,
            "process_type_selected": False,
            "procedure_selected": False,
            "contract_type_selected": False,
            "other_currency_no_selected": False,
            "general_data_completed": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchGeneralDataDraftProbeResult:
            return BatchGeneralDataDraftProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                header_validation_confirmed=flags[
                    "header_validation_confirmed"
                ],
                object_written=flags["object_written"],
                signing_date_written=flags["signing_date_written"],
                starting_date_written=flags["starting_date_written"],
                amount_written=flags["amount_written"],
                amount_in_words_generated=flags[
                    "amount_in_words_generated"
                ],
                contract_term_written=flags["contract_term_written"],
                term_unit_days_selected=flags[
                    "term_unit_days_selected"
                ],
                process_type_selected=flags["process_type_selected"],
                procedure_selected=flags["procedure_selected"],
                contract_type_selected=flags["contract_type_selected"],
                other_currency_no_selected=flags[
                    "other_currency_no_selected"
                ],
                general_data_completed=flags["general_data_completed"],
                general_validate_clicked=False,
                save_clicked=False,
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña."
                            ),
                        )
                    return result(
                        success=False,
                        code="AUTHENTICATED_STATE_UNCONFIRMED",
                        message=(
                            "El portal respondió, pero no fue posible "
                            "confirmar el estado autenticado."
                        ),
                    )

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )
                flags["header_validation_confirmed"] = True

                flags.update(
                    self._populate_general_data_draft(
                        driver=session.driver,
                        waits=waits,
                        resolver=resolver,
                        contract=contract,
                    )
                )
                flags["general_data_completed"] = all(
                    flags[name]
                    for name in (
                        "object_written",
                        "signing_date_written",
                        "starting_date_written",
                        "amount_written",
                        "amount_in_words_generated",
                        "contract_term_written",
                        "term_unit_days_selected",
                        "process_type_selected",
                        "procedure_selected",
                        "contract_type_selected",
                        "other_currency_no_selected",
                    )
                )

                return result(
                    success=flags["general_data_completed"],
                    code=(
                        "GENERAL_DATA_DRAFT_READY"
                        if flags["general_data_completed"]
                        else "GENERAL_DATA_DRAFT_INCOMPLETE"
                    ),
                    message=(
                        "Se completaron y confirmaron los datos generales C3. "
                        "No se pulsó la validación general ni Guardar."
                        if flags["general_data_completed"]
                        else (
                            "La carga C3 terminó sin confirmar todos los "
                            "valores esperados."
                        )
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "GENERAL_DATA_DRAFT_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="GENERAL_DATA_DRAFT_ERROR",
                message=(
                    "La carga diagnóstica C3 terminó con un error "
                    f"controlado: {type(error).__name__}."
                ),
            )

    def _probe_general_completion_draft_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchGeneralCompletionDraftProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "header_validation_confirmed": False,
            "general_data_completed": False,
            "government_plan_selected": False,
            "budget_year_selected": False,
            "budget_item_selected": False,
            "budget_subsector_selected": False,
            "budget_link_clicked": False,
            "secop_yes_selected": False,
            "secop_url_written": False,
            "advance_no_selected": False,
            "commercial_trust_no_selected": False,
            "urgency_no_selected": False,
            "future_commitment_no_selected": False,
            "cooperation_contract_no_selected": False,
            "execution_department_selected": False,
            "execution_city_selected": False,
            "final_validate_button_found": False,
            "general_completion_completed": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchGeneralCompletionDraftProbeResult:
            return BatchGeneralCompletionDraftProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                header_validation_confirmed=flags[
                    "header_validation_confirmed"
                ],
                general_data_completed=flags["general_data_completed"],
                government_plan_selected=flags[
                    "government_plan_selected"
                ],
                budget_year_selected=flags["budget_year_selected"],
                budget_item_selected=flags["budget_item_selected"],
                budget_subsector_selected=flags[
                    "budget_subsector_selected"
                ],
                budget_link_clicked=flags["budget_link_clicked"],
                secop_yes_selected=flags["secop_yes_selected"],
                secop_url_written=flags["secop_url_written"],
                advance_no_selected=flags["advance_no_selected"],
                commercial_trust_no_selected=flags[
                    "commercial_trust_no_selected"
                ],
                urgency_no_selected=flags["urgency_no_selected"],
                future_commitment_no_selected=flags[
                    "future_commitment_no_selected"
                ],
                cooperation_contract_no_selected=flags[
                    "cooperation_contract_no_selected"
                ],
                execution_department_selected=flags[
                    "execution_department_selected"
                ],
                execution_city_selected=flags["execution_city_selected"],
                final_validate_button_found=flags[
                    "final_validate_button_found"
                ],
                general_completion_completed=flags[
                    "general_completion_completed"
                ],
                general_validate_clicked=False,
                save_clicked=False,
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña."
                            ),
                        )
                    return result(
                        success=False,
                        code="AUTHENTICATED_STATE_UNCONFIRMED",
                        message=(
                            "El portal respondió, pero no fue posible "
                            "confirmar el estado autenticado."
                        ),
                    )

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )
                flags["header_validation_confirmed"] = True

                general_flags = self._populate_general_data_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                flags["general_data_completed"] = all(
                    general_flags.values()
                )
                if not flags["general_data_completed"]:
                    return result(
                        success=False,
                        code="GENERAL_DATA_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos generales C3 "
                            "antes de completar C4."
                        ),
                    )

                flags.update(
                    self._populate_general_completion_draft(
                        driver=session.driver,
                        waits=waits,
                        resolver=resolver,
                        contract=contract,
                    )
                )
                flags["general_completion_completed"] = all(
                    flags[name]
                    for name in (
                        "government_plan_selected",
                        "budget_year_selected",
                        "budget_item_selected",
                        "budget_subsector_selected",
                        "budget_link_clicked",
                        "secop_yes_selected",
                        "secop_url_written",
                        "advance_no_selected",
                        "commercial_trust_no_selected",
                        "urgency_no_selected",
                        "future_commitment_no_selected",
                        "cooperation_contract_no_selected",
                        "execution_department_selected",
                        "execution_city_selected",
                        "final_validate_button_found",
                    )
                )

                return result(
                    success=flags["general_completion_completed"],
                    code=(
                        "GENERAL_COMPLETION_DRAFT_READY"
                        if flags["general_completion_completed"]
                        else "GENERAL_COMPLETION_DRAFT_INCOMPLETE"
                    ),
                    message=(
                        "Se completaron y confirmaron los datos C3-C4. No se "
                        "pulsó la validación general ni Guardar."
                        if flags["general_completion_completed"]
                        else (
                            "La carga C4 terminó sin confirmar todos los "
                            "valores esperados."
                        )
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "GENERAL_COMPLETION_DRAFT_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="GENERAL_COMPLETION_DRAFT_ERROR",
                message=(
                    "La carga diagnóstica C4 terminó con un error "
                    f"controlado: {type(error).__name__}."
                ),
            )


    def _probe_general_validation_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchGeneralValidationProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "header_validation_confirmed": False,
            "general_data_completed": False,
            "general_completion_completed": False,
            "final_validate_button_found": False,
            "general_validate_clicked": False,
            "general_validation_confirmed": False,
            "save_button_found": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchGeneralValidationProbeResult:
            return BatchGeneralValidationProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                header_validation_confirmed=flags[
                    "header_validation_confirmed"
                ],
                general_data_completed=flags["general_data_completed"],
                general_completion_completed=flags[
                    "general_completion_completed"
                ],
                final_validate_button_found=flags[
                    "final_validate_button_found"
                ],
                general_validate_clicked=flags[
                    "general_validate_clicked"
                ],
                general_validation_confirmed=flags[
                    "general_validation_confirmed"
                ],
                save_button_found=flags["save_button_found"],
                save_clicked=False,
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña."
                            ),
                        )
                    return result(
                        success=False,
                        code="AUTHENTICATED_STATE_UNCONFIRMED",
                        message=(
                            "El portal respondió, pero no fue posible "
                            "confirmar el estado autenticado."
                        ),
                    )

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )
                flags["header_validation_confirmed"] = True

                general_flags = self._populate_general_data_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                flags["general_data_completed"] = all(
                    general_flags.values()
                )
                if not flags["general_data_completed"]:
                    return result(
                        success=False,
                        code="GENERAL_DATA_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos generales C3 "
                            "antes de la validación final."
                        ),
                    )

                completion_flags = self._populate_general_completion_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                flags["final_validate_button_found"] = completion_flags[
                    "final_validate_button_found"
                ]
                flags["general_completion_completed"] = all(
                    completion_flags.values()
                )
                if not flags["general_completion_completed"]:
                    return result(
                        success=False,
                        code="GENERAL_COMPLETION_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C4 antes de "
                            "la validación general."
                        ),
                    )

                validation_flags = self._validate_general_form_without_saving(
                    driver=session.driver,
                    resolver=resolver,
                )
                flags.update(validation_flags)

                ready = all(
                    flags[name]
                    for name in (
                        "header_validation_confirmed",
                        "general_data_completed",
                        "general_completion_completed",
                        "final_validate_button_found",
                        "general_validate_clicked",
                        "general_validation_confirmed",
                        "save_button_found",
                    )
                )

                return result(
                    success=ready,
                    code=(
                        "GENERAL_VALIDATION_READY"
                        if ready
                        else "GENERAL_VALIDATION_INCOMPLETE"
                    ),
                    message=(
                        "Los datos C3-C4 fueron validados y se confirmó que "
                        "Guardar está disponible. No se pulsó Guardar."
                        if ready
                        else (
                            "La validación general terminó sin confirmar "
                            "todas las postcondiciones esperadas."
                        )
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "GENERAL_VALIDATION_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="GENERAL_VALIDATION_ERROR",
                message=(
                    "La validación diagnóstica de C3-C4 terminó con un error "
                    f"controlado: {type(error).__name__}."
                ),
            )

    def _probe_contract_save_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchContractSaveProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "header_validation_confirmed": False,
            "general_data_completed": False,
            "general_completion_completed": False,
            "general_validation_confirmed": False,
            "save_button_found": False,
            "save_clicked": False,
            "success_dialog_found": False,
            "success_dialog_accepted": False,
            "contract_saved_confirmed": False,
            "supervisor_section_found": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchContractSaveProbeResult:
            return BatchContractSaveProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                header_validation_confirmed=flags[
                    "header_validation_confirmed"
                ],
                general_data_completed=flags["general_data_completed"],
                general_completion_completed=flags[
                    "general_completion_completed"
                ],
                general_validation_confirmed=flags[
                    "general_validation_confirmed"
                ],
                save_button_found=flags["save_button_found"],
                save_clicked=flags["save_clicked"],
                success_dialog_found=flags[
                    "success_dialog_found"
                ],
                success_dialog_accepted=flags[
                    "success_dialog_accepted"
                ],
                contract_saved_confirmed=flags[
                    "contract_saved_confirmed"
                ],
                supervisor_section_found=flags[
                    "supervisor_section_found"
                ],
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña."
                            ),
                        )
                    return result(
                        success=False,
                        code="AUTHENTICATED_STATE_UNCONFIRMED",
                        message=(
                            "El portal respondió, pero no fue posible "
                            "confirmar el estado autenticado."
                        ),
                    )

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )
                flags["header_validation_confirmed"] = True

                general_flags = self._populate_general_data_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                flags["general_data_completed"] = all(general_flags.values())
                if not flags["general_data_completed"]:
                    return result(
                        success=False,
                        code="GENERAL_DATA_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C3 antes "
                            "del guardado."
                        ),
                    )

                completion_flags = self._populate_general_completion_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                flags["general_completion_completed"] = all(
                    completion_flags.values()
                )
                if not flags["general_completion_completed"]:
                    return result(
                        success=False,
                        code="GENERAL_COMPLETION_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C4 antes "
                            "del guardado."
                        ),
                    )

                validation_flags = self._validate_general_form_without_saving(
                    driver=session.driver,
                    resolver=resolver,
                )
                flags["general_validation_confirmed"] = validation_flags[
                    "general_validation_confirmed"
                ]
                flags["save_button_found"] = validation_flags[
                    "save_button_found"
                ]

                save_flags = self._save_contract_and_confirm(
                    driver=session.driver,
                    resolver=resolver,
                    contract=contract,
                )
                flags.update(save_flags)

                ready = all(flags.values())
                return result(
                    success=ready,
                    code=(
                        "CONTRACT_SAVE_READY"
                        if ready
                        else "CONTRACT_SAVE_INCOMPLETE"
                    ),
                    message=(
                        "El contrato fue guardado y se confirmó la apertura "
                        "de la etapa de supervisor."
                        if ready
                        else (
                            "El guardado terminó sin confirmar todas las "
                            "postcondiciones esperadas."
                        )
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "CONTRACT_SAVE_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="CONTRACT_SAVE_ERROR",
                message=(
                    "El guardado controlado terminó con un error "
                    f"controlado: {type(error).__name__}."
                ),
            )

    def _probe_contract_supervisor_link_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchContractSupervisorLinkProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "contract_saved_confirmed": False,
            "supervisor_section_found": False,
            "supervisor_dialog_opened": False,
            "supervisor_nature_selected": False,
            "supervisor_id_type_selected": False,
            "supervisor_document_written": False,
            "supervisor_result_found": False,
            "supervisor_selected": False,
            "supervisor_type_internal_confirmed": False,
            "supervisor_validate_clicked": False,
            "supervisor_validation_confirmed": False,
            "supervisor_link_clicked": False,
            "success_dialog_found": False,
            "success_dialog_accepted": False,
            "supervisor_linked_confirmed": False,
            "availability_section_found": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchContractSupervisorLinkProbeResult:
            return BatchContractSupervisorLinkProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                contract_saved_confirmed=flags[
                    "contract_saved_confirmed"
                ],
                supervisor_section_found=flags[
                    "supervisor_section_found"
                ],
                supervisor_dialog_opened=flags[
                    "supervisor_dialog_opened"
                ],
                supervisor_nature_selected=flags[
                    "supervisor_nature_selected"
                ],
                supervisor_id_type_selected=flags[
                    "supervisor_id_type_selected"
                ],
                supervisor_document_written=flags[
                    "supervisor_document_written"
                ],
                supervisor_result_found=flags[
                    "supervisor_result_found"
                ],
                supervisor_selected=flags[
                    "supervisor_selected"
                ],
                supervisor_type_internal_confirmed=flags[
                    "supervisor_type_internal_confirmed"
                ],
                supervisor_validate_clicked=flags[
                    "supervisor_validate_clicked"
                ],
                supervisor_validation_confirmed=flags[
                    "supervisor_validation_confirmed"
                ],
                supervisor_link_clicked=flags[
                    "supervisor_link_clicked"
                ],
                success_dialog_found=flags[
                    "success_dialog_found"
                ],
                success_dialog_accepted=flags[
                    "success_dialog_accepted"
                ],
                supervisor_linked_confirmed=flags[
                    "supervisor_linked_confirmed"
                ],
                availability_section_found=flags[
                    "availability_section_found"
                ],
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña configurados."
                            ),
                        )
                    raise

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )

                general_flags = self._populate_general_data_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                if not all(general_flags.values()):
                    return result(
                        success=False,
                        code="GENERAL_DATA_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C3 antes "
                            "del guardado."
                        ),
                    )

                completion_flags = self._populate_general_completion_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                if not all(completion_flags.values()):
                    return result(
                        success=False,
                        code="GENERAL_COMPLETION_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C4 antes "
                            "del guardado."
                        ),
                    )

                validation_flags = self._validate_general_form_without_saving(
                    driver=session.driver,
                    resolver=resolver,
                )
                if not (
                    validation_flags["general_validation_confirmed"]
                    and validation_flags["save_button_found"]
                ):
                    return result(
                        success=False,
                        code="GENERAL_VALIDATION_INCOMPLETE",
                        message=(
                            "La validación general no habilitó Guardar."
                        ),
                    )

                save_flags = self._save_contract_and_confirm(
                    driver=session.driver,
                    resolver=resolver,
                    contract=contract,
                )
                flags["contract_saved_confirmed"] = save_flags[
                    "contract_saved_confirmed"
                ]
                flags["supervisor_section_found"] = save_flags[
                    "supervisor_section_found"
                ]
                if not (
                    flags["contract_saved_confirmed"]
                    and flags["supervisor_section_found"]
                ):
                    return result(
                        success=False,
                        code="CONTRACT_SAVE_INCOMPLETE",
                        message=(
                            "El contrato no quedó confirmado en la etapa "
                            "de supervisor."
                        ),
                    )

                supervisor_flags = self._link_supervisor_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                    progress=flags,
                )
                flags.update(supervisor_flags)

                ready = all(flags.values())
                return result(
                    success=ready,
                    code=(
                        "CONTRACT_SUPERVISOR_LINK_READY"
                        if ready
                        else "CONTRACT_SUPERVISOR_LINK_INCOMPLETE"
                    ),
                    message=(
                        "El contrato fue guardado y el supervisor interno "
                        "quedó vinculado. Se confirmó la etapa de "
                        "disponibilidad presupuestal."
                        if ready
                        else (
                            "El flujo terminó sin confirmar todas las "
                            "postcondiciones del supervisor."
                        )
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "CONTRACT_SUPERVISOR_LINK_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="CONTRACT_SUPERVISOR_LINK_ERROR",
                message=(
                    "El guardado y vinculación del supervisor terminó con "
                    f"un error controlado: {type(error).__name__}."
                ),
            )

    def _probe_contract_availability_link_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchContractAvailabilityLinkProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "contract_saved_confirmed": False,
            "supervisor_section_found": False,
            "supervisor_dialog_opened": False,
            "supervisor_nature_selected": False,
            "supervisor_id_type_selected": False,
            "supervisor_document_written": False,
            "supervisor_result_found": False,
            "supervisor_selected": False,
            "supervisor_type_internal_confirmed": False,
            "supervisor_validate_clicked": False,
            "supervisor_validation_confirmed": False,
            "supervisor_link_clicked": False,
            "success_dialog_found": False,
            "success_dialog_accepted": False,
            "supervisor_linked_confirmed": False,
            "availability_section_found": False,
            "availability_search_written": False,
            "availability_result_found": False,
            "availability_result_matches": False,
            "availability_link_clicked": False,
            "availability_link_success_found": False,
            "availability_linked_row_confirmed": False,
            "continue_button_found": False,
            "continue_clicked": False,
            "budget_register_section_found": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchContractAvailabilityLinkProbeResult:
            return BatchContractAvailabilityLinkProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                contract_saved_confirmed=flags[
                    "contract_saved_confirmed"
                ],
                supervisor_section_found=flags[
                    "supervisor_section_found"
                ],
                supervisor_dialog_opened=flags[
                    "supervisor_dialog_opened"
                ],
                supervisor_nature_selected=flags[
                    "supervisor_nature_selected"
                ],
                supervisor_id_type_selected=flags[
                    "supervisor_id_type_selected"
                ],
                supervisor_document_written=flags[
                    "supervisor_document_written"
                ],
                supervisor_result_found=flags[
                    "supervisor_result_found"
                ],
                supervisor_selected=flags[
                    "supervisor_selected"
                ],
                supervisor_type_internal_confirmed=flags[
                    "supervisor_type_internal_confirmed"
                ],
                supervisor_validate_clicked=flags[
                    "supervisor_validate_clicked"
                ],
                supervisor_validation_confirmed=flags[
                    "supervisor_validation_confirmed"
                ],
                supervisor_link_clicked=flags[
                    "supervisor_link_clicked"
                ],
                supervisor_linked_confirmed=flags[
                    "supervisor_linked_confirmed"
                ],
                availability_section_found=flags[
                    "availability_section_found"
                ],
                availability_search_written=flags[
                    "availability_search_written"
                ],
                availability_result_found=flags[
                    "availability_result_found"
                ],
                availability_result_matches=flags[
                    "availability_result_matches"
                ],
                availability_link_clicked=flags[
                    "availability_link_clicked"
                ],
                availability_link_success_found=flags[
                    "availability_link_success_found"
                ],
                availability_linked_row_confirmed=flags[
                    "availability_linked_row_confirmed"
                ],
                continue_button_found=flags[
                    "continue_button_found"
                ],
                continue_clicked=flags[
                    "continue_clicked"
                ],
                budget_register_section_found=flags[
                    "budget_register_section_found"
                ],
                supervisor_success_dialog_found=flags[
                    "success_dialog_found"
                ],
                supervisor_success_dialog_accepted=flags[
                    "success_dialog_accepted"
                ],
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña configurados."
                            ),
                        )
                    raise

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )

                general_flags = self._populate_general_data_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                if not all(general_flags.values()):
                    return result(
                        success=False,
                        code="GENERAL_DATA_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C3 antes "
                            "del guardado."
                        ),
                    )

                completion_flags = self._populate_general_completion_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                if not all(completion_flags.values()):
                    return result(
                        success=False,
                        code="GENERAL_COMPLETION_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C4 antes "
                            "del guardado."
                        ),
                    )

                validation_flags = self._validate_general_form_without_saving(
                    driver=session.driver,
                    resolver=resolver,
                )
                if not (
                    validation_flags["general_validation_confirmed"]
                    and validation_flags["save_button_found"]
                ):
                    return result(
                        success=False,
                        code="GENERAL_VALIDATION_INCOMPLETE",
                        message=(
                            "La validación general no habilitó Guardar."
                        ),
                    )

                save_flags = self._save_contract_and_confirm(
                    driver=session.driver,
                    resolver=resolver,
                    contract=contract,
                )
                flags["contract_saved_confirmed"] = save_flags[
                    "contract_saved_confirmed"
                ]
                flags["supervisor_section_found"] = save_flags[
                    "supervisor_section_found"
                ]
                if not (
                    flags["contract_saved_confirmed"]
                    and flags["supervisor_section_found"]
                ):
                    return result(
                        success=False,
                        code="CONTRACT_SAVE_INCOMPLETE",
                        message=(
                            "El contrato no quedó confirmado en la etapa "
                            "de supervisor."
                        ),
                    )

                supervisor_flags = self._link_supervisor_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                    progress=flags,
                )
                flags.update(supervisor_flags)

                availability_flags = self._link_availability_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    expected_cdp=contract.budget.cdp_code,
                )
                flags.update(availability_flags)

                ready = all(flags.values())
                return result(
                    success=ready,
                    code=(
                        "CONTRACT_AVAILABILITY_LINK_READY"
                        if ready
                        else "CONTRACT_AVAILABILITY_LINK_INCOMPLETE"
                    ),
                    message=(
                        "El contrato, el supervisor interno y la "
                        "disponibilidad presupuestal quedaron vinculados. "
                        "Se confirmó la etapa de registro presupuestal."
                        if ready
                        else (
                            "El flujo terminó sin confirmar todas las "
                            "postcondiciones del CDP."
                        )
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "CONTRACT_AVAILABILITY_LINK_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="CONTRACT_AVAILABILITY_LINK_ERROR",
                message=(
                    "El guardado, supervisor y CDP terminaron con "
                    f"un error controlado: {type(error).__name__}."
                ),
            )


    def _probe_contract_budget_register_link_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchContractBudgetRegisterLinkProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "contract_saved_confirmed": False,
            "supervisor_section_found": False,
            "supervisor_dialog_opened": False,
            "supervisor_nature_selected": False,
            "supervisor_id_type_selected": False,
            "supervisor_document_written": False,
            "supervisor_result_found": False,
            "supervisor_selected": False,
            "supervisor_type_internal_confirmed": False,
            "supervisor_validate_clicked": False,
            "supervisor_validation_confirmed": False,
            "supervisor_link_clicked": False,
            "success_dialog_found": False,
            "success_dialog_accepted": False,
            "supervisor_linked_confirmed": False,
            "availability_section_found": False,
            "availability_search_written": False,
            "availability_result_found": False,
            "availability_result_matches": False,
            "availability_link_clicked": False,
            "availability_link_success_found": False,
            "availability_linked_row_confirmed": False,
            "continue_button_found": False,
            "continue_clicked": False,
            "budget_register_section_found": False,
            "budget_register_number_written": False,
            "budget_register_date_provided": (
                contract.budget.budget_register_date is not None
            ),
            "budget_register_date_written": False,
            "budget_register_availability_selected": False,
            "gross_total_written": False,
            "budget_register_validate_clicked": False,
            "budget_register_validation_confirmed": False,
            "budget_register_link_clicked": False,
            "budget_register_success_dialog_found": False,
            "budget_register_success_dialog_accepted": False,
            "budget_register_linked_confirmed": False,
            "additional_dates_section_found": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchContractBudgetRegisterLinkProbeResult:
            return BatchContractBudgetRegisterLinkProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                contract_saved_confirmed=flags[
                    "contract_saved_confirmed"
                ],
                supervisor_section_found=flags[
                    "supervisor_section_found"
                ],
                supervisor_dialog_opened=flags[
                    "supervisor_dialog_opened"
                ],
                supervisor_nature_selected=flags[
                    "supervisor_nature_selected"
                ],
                supervisor_id_type_selected=flags[
                    "supervisor_id_type_selected"
                ],
                supervisor_document_written=flags[
                    "supervisor_document_written"
                ],
                supervisor_result_found=flags[
                    "supervisor_result_found"
                ],
                supervisor_selected=flags[
                    "supervisor_selected"
                ],
                supervisor_type_internal_confirmed=flags[
                    "supervisor_type_internal_confirmed"
                ],
                supervisor_validate_clicked=flags[
                    "supervisor_validate_clicked"
                ],
                supervisor_validation_confirmed=flags[
                    "supervisor_validation_confirmed"
                ],
                supervisor_link_clicked=flags[
                    "supervisor_link_clicked"
                ],
                supervisor_linked_confirmed=flags[
                    "supervisor_linked_confirmed"
                ],
                availability_section_found=flags[
                    "availability_section_found"
                ],
                availability_search_written=flags[
                    "availability_search_written"
                ],
                availability_result_found=flags[
                    "availability_result_found"
                ],
                availability_result_matches=flags[
                    "availability_result_matches"
                ],
                availability_link_clicked=flags[
                    "availability_link_clicked"
                ],
                availability_link_success_found=flags[
                    "availability_link_success_found"
                ],
                availability_linked_row_confirmed=flags[
                    "availability_linked_row_confirmed"
                ],
                continue_button_found=flags[
                    "continue_button_found"
                ],
                continue_clicked=flags[
                    "continue_clicked"
                ],
                budget_register_section_found=flags[
                    "budget_register_section_found"
                ],
                budget_register_number_written=flags[
                    "budget_register_number_written"
                ],
                budget_register_date_provided=flags[
                    "budget_register_date_provided"
                ],
                budget_register_date_written=flags[
                    "budget_register_date_written"
                ],
                budget_register_availability_selected=flags[
                    "budget_register_availability_selected"
                ],
                gross_total_written=flags[
                    "gross_total_written"
                ],
                budget_register_validate_clicked=flags[
                    "budget_register_validate_clicked"
                ],
                budget_register_validation_confirmed=flags[
                    "budget_register_validation_confirmed"
                ],
                budget_register_link_clicked=flags[
                    "budget_register_link_clicked"
                ],
                budget_register_success_dialog_found=flags[
                    "budget_register_success_dialog_found"
                ],
                budget_register_success_dialog_accepted=flags[
                    "budget_register_success_dialog_accepted"
                ],
                budget_register_linked_confirmed=flags[
                    "budget_register_linked_confirmed"
                ],
                additional_dates_section_found=flags[
                    "additional_dates_section_found"
                ],
                supervisor_success_dialog_found=flags[
                    "success_dialog_found"
                ],
                supervisor_success_dialog_accepted=flags[
                    "success_dialog_accepted"
                ],
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña configurados."
                            ),
                        )
                    raise

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )

                general_flags = self._populate_general_data_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                if not all(general_flags.values()):
                    return result(
                        success=False,
                        code="GENERAL_DATA_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C3 antes "
                            "del guardado."
                        ),
                    )

                completion_flags = self._populate_general_completion_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                if not all(completion_flags.values()):
                    return result(
                        success=False,
                        code="GENERAL_COMPLETION_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C4 antes "
                            "del guardado."
                        ),
                    )

                validation_flags = self._validate_general_form_without_saving(
                    driver=session.driver,
                    resolver=resolver,
                )
                if not (
                    validation_flags["general_validation_confirmed"]
                    and validation_flags["save_button_found"]
                ):
                    return result(
                        success=False,
                        code="GENERAL_VALIDATION_INCOMPLETE",
                        message=(
                            "La validación general no habilitó Guardar."
                        ),
                    )

                save_flags = self._save_contract_and_confirm(
                    driver=session.driver,
                    resolver=resolver,
                    contract=contract,
                )
                flags["contract_saved_confirmed"] = save_flags[
                    "contract_saved_confirmed"
                ]
                flags["supervisor_section_found"] = save_flags[
                    "supervisor_section_found"
                ]
                if not (
                    flags["contract_saved_confirmed"]
                    and flags["supervisor_section_found"]
                ):
                    return result(
                        success=False,
                        code="CONTRACT_SAVE_INCOMPLETE",
                        message=(
                            "El contrato no quedó confirmado en la etapa "
                            "de supervisor."
                        ),
                    )

                supervisor_flags = self._link_supervisor_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                    progress=flags,
                )
                flags.update(supervisor_flags)

                availability_flags = self._link_availability_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    expected_cdp=contract.budget.cdp_code,
                )
                flags.update(availability_flags)

                budget_register_flags = (
                    self._link_budget_register_and_confirm(
                        driver=session.driver,
                        waits=waits,
                        resolver=resolver,
                        contract=contract,
                    )
                )
                flags.update(budget_register_flags)

                required_flags = (
                    "contract_saved_confirmed",
                    "supervisor_linked_confirmed",
                    "availability_linked_row_confirmed",
                    "budget_register_section_found",
                    "budget_register_number_written",
                    "budget_register_availability_selected",
                    "gross_total_written",
                    "budget_register_validate_clicked",
                    "budget_register_validation_confirmed",
                    "budget_register_link_clicked",
                    "budget_register_success_dialog_found",
                    "budget_register_success_dialog_accepted",
                    "budget_register_linked_confirmed",
                    "additional_dates_section_found",
                )
                date_ready = (
                    not flags["budget_register_date_provided"]
                    or flags["budget_register_date_written"]
                )
                ready = (
                    all(flags[key] for key in required_flags)
                    and date_ready
                )
                return result(
                    success=ready,
                    code=(
                        "CONTRACT_BUDGET_REGISTER_LINK_READY"
                        if ready
                        else "CONTRACT_BUDGET_REGISTER_LINK_INCOMPLETE"
                    ),
                    message=(
                        "El contrato, el supervisor, el CDP y el registro "
                        "presupuestal quedaron vinculados. Se confirmó la "
                        "etapa de fechas adicionales."
                        if ready
                        else (
                            "El flujo terminó sin confirmar todas las "
                            "postcondiciones del registro presupuestal."
                        )
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "CONTRACT_BUDGET_REGISTER_LINK_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="CONTRACT_BUDGET_REGISTER_LINK_ERROR",
                message=(
                    "El guardado, supervisor, CDP y RP terminaron con "
                    f"un error controlado: {type(error).__name__}."
                ),
            )

    def _probe_contract_additional_dates_link_in_browser(
        self,
        *,
        username: str,
        password: str,
        contract: ContractData,
        started: float,
    ) -> BatchContractAdditionalDatesLinkProbeResult:
        authenticated = False
        assistant_opened = False
        flags = {
            "contract_saved_confirmed": False,
            "supervisor_linked_confirmed": False,
            "availability_linked_row_confirmed": False,
            "budget_register_linked_confirmed": False,
            "additional_dates_section_found": False,
            "additional_dates_any_provided": any((
                contract.guarantee_approval_date is not None,
                contract.website_publication_date is not None,
                contract.secop_publication_date is not None,
            )),
            "guarantee_approval_date_provided": (
                contract.guarantee_approval_date is not None
            ),
            "guarantee_approval_date_written": False,
            "website_publication_date_provided": (
                contract.website_publication_date is not None
            ),
            "website_publication_date_written": False,
            "secop_publication_date_provided": (
                contract.secop_publication_date is not None
            ),
            "secop_publication_date_written": False,
            "additional_dates_validate_clicked": False,
            "additional_dates_validation_confirmed": False,
            "additional_dates_link_clicked": False,
            "additional_dates_success_dialog_found": False,
            "additional_dates_success_dialog_accepted": False,
            "additional_dates_skipped": False,
            "additional_dates_linked_confirmed": False,
            "file_reported_section_found": False,
        }

        def result(
            *,
            success: bool,
            code: str,
            message: str,
        ) -> BatchContractAdditionalDatesLinkProbeResult:
            return BatchContractAdditionalDatesLinkProbeResult(
                success=success,
                code=code,
                message=message,
                authenticated=authenticated,
                assistant_opened=assistant_opened,
                duration_ms=max(
                    0,
                    round((monotonic() - started) * 1000),
                ),
                **flags,
            )

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
                except PortalTimeoutError:
                    if resolver.optional_visible(
                        "portal.login.password",
                        timeout_seconds=2.0,
                    ) is not None:
                        return result(
                            success=False,
                            code="INVALID_CREDENTIALS",
                            message=(
                                "Gestión Transparente rechazó el usuario o la "
                                "contraseña configurados."
                            ),
                        )
                    raise

                authenticated = True
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.contracting_menu",
                    target_key="navigation.enter_contract",
                    step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
                    step_label="Contratación",
                )
                self._ensure_target_visible(
                    driver=session.driver,
                    resolver=resolver,
                    toggle_key="navigation.enter_contract",
                    target_key="assistant.open",
                    step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
                    step_label="Ingresar Contrato",
                )
                self._open_assistant_form(
                    driver=session.driver,
                    resolver=resolver,
                )
                assistant_opened = True

                self._populate_header_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                self._click_and_confirm_visible(
                    driver=session.driver,
                    resolver=resolver,
                    click_key="contract.header.validate_button",
                    target_key="contract.header.validation_success",
                    code="HEADER_VALIDATION_TIMEOUT",
                    label="la validación del encabezado C1-C2",
                )

                general_flags = self._populate_general_data_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                if not all(general_flags.values()):
                    return result(
                        success=False,
                        code="GENERAL_DATA_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C3 antes "
                            "del guardado."
                        ),
                    )

                completion_flags = self._populate_general_completion_draft(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                if not all(completion_flags.values()):
                    return result(
                        success=False,
                        code="GENERAL_COMPLETION_DRAFT_INCOMPLETE",
                        message=(
                            "No se confirmaron todos los datos C4 antes "
                            "del guardado."
                        ),
                    )

                validation_flags = self._validate_general_form_without_saving(
                    driver=session.driver,
                    resolver=resolver,
                )
                if not (
                    validation_flags["general_validation_confirmed"]
                    and validation_flags["save_button_found"]
                ):
                    return result(
                        success=False,
                        code="GENERAL_VALIDATION_INCOMPLETE",
                        message="La validación general no habilitó Guardar.",
                    )

                save_flags = self._save_contract_and_confirm(
                    driver=session.driver,
                    resolver=resolver,
                    contract=contract,
                )
                flags["contract_saved_confirmed"] = save_flags[
                    "contract_saved_confirmed"
                ]
                if not save_flags["supervisor_section_found"]:
                    return result(
                        success=False,
                        code="CONTRACT_SAVE_INCOMPLETE",
                        message=(
                            "El contrato no quedó confirmado en la etapa "
                            "de supervisor."
                        ),
                    )

                supervisor_flags = self._link_supervisor_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                flags["supervisor_linked_confirmed"] = supervisor_flags[
                    "supervisor_linked_confirmed"
                ]

                availability_flags = self._link_availability_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    expected_cdp=contract.budget.cdp_code,
                )
                flags["availability_linked_row_confirmed"] = (
                    availability_flags["availability_linked_row_confirmed"]
                )

                budget_register_flags = self._link_budget_register_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                flags["budget_register_linked_confirmed"] = (
                    budget_register_flags["budget_register_linked_confirmed"]
                )
                flags["additional_dates_section_found"] = (
                    budget_register_flags["additional_dates_section_found"]
                )

                date_flags = self._link_additional_dates_and_confirm(
                    driver=session.driver,
                    waits=waits,
                    resolver=resolver,
                    contract=contract,
                )
                flags.update(date_flags)

                ready = all((
                    flags["contract_saved_confirmed"],
                    flags["supervisor_linked_confirmed"],
                    flags["availability_linked_row_confirmed"],
                    flags["budget_register_linked_confirmed"],
                    flags["additional_dates_section_found"],
                    flags["additional_dates_linked_confirmed"],
                    flags["file_reported_section_found"],
                ))
                return result(
                    success=ready,
                    code=(
                        "CONTRACT_ADDITIONAL_DATES_LINK_READY"
                        if ready
                        else "CONTRACT_ADDITIONAL_DATES_LINK_INCOMPLETE"
                    ),
                    message=(
                        "El contrato quedó registrado hasta la vinculación "
                        "de fechas adicionales. Se confirmó la pantalla de "
                        "archivos reportados sin gestionar adjuntos."
                        if ready
                        else (
                            "El flujo terminó sin confirmar todas las "
                            "postcondiciones de fechas adicionales."
                        )
                    ),
                )

        except BrowserStartupError:
            return result(
                success=False,
                code="BROWSER_UNAVAILABLE",
                message="No fue posible iniciar Google Chrome.",
            )
        except PortalTimeoutError as error:
            return result(
                success=False,
                code=(
                    error.code
                    if error.code != "PORTAL_TIMEOUT"
                    else "CONTRACT_ADDITIONAL_DATES_LINK_TIMEOUT"
                ),
                message=str(error),
            )
        except Exception as error:
            return result(
                success=False,
                code="CONTRACT_ADDITIONAL_DATES_LINK_ERROR",
                message=(
                    "El guardado hasta fechas adicionales terminó con "
                    f"un error controlado: {type(error).__name__}."
                ),
            )


    def _save_contract_and_confirm(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        contract: ContractData,
    ) -> dict[str, bool]:
        """Pulsa Guardar, acepta el diálogo y confirma la siguiente etapa."""

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="general.save_button",
            target_key="general.save_success_dialog",
            code="CONTRACT_SAVE_DIALOG_TIMEOUT",
            label="el diálogo de guardado exitoso",
        )

        accepted = False
        saved_identifier = None
        supervisor_section = None
        errors: list[str] = []

        for mode in ("native", "actions", "javascript"):
            accept_button = resolver.clickable(
                "general.save_success_accept",
                timeout_seconds=self._timeout_seconds,
            )
            self._scroll_into_view(driver, accept_button)
            try:
                self._perform_click(
                    driver=driver,
                    element=accept_button,
                    mode=mode,
                )
            except WebDriverException as error:
                errors.append(f"{mode}: {type(error).__name__}")
                continue

            saved_identifier = resolver.optional_visible(
                "general.contract_saved",
                timeout_seconds=self._timeout_seconds,
            )
            supervisor_section = resolver.optional_visible(
                "supervisor.section",
                timeout_seconds=self._timeout_seconds,
            )
            if saved_identifier is not None or supervisor_section is not None:
                accepted = True
                break
            errors.append(f"{mode}: sin siguiente etapa")

        if not accepted:
            raise PortalTimeoutError(
                "El portal confirmó el guardado, pero no abrió la etapa "
                "siguiente.",
                code="CONTRACT_SAVE_ACCEPT_TIMEOUT",
                metadata={"click_attempts": errors},
            )

        candidate = ""
        if saved_identifier is not None:
            candidate = str(
                saved_identifier.get_attribute("value")
                or saved_identifier.text
                or ""
            ).strip()

        contract_saved_confirmed = False
        if candidate:
            normalized_candidate = self._normalize_identity(candidate)
            expected_values = (
                self._normalize_identity(contract.contract_number),
                self._normalize_identity(
                    contract.contractor.document_number
                ),
            )
            contract_saved_confirmed = any(
                expected
                and (
                    normalized_candidate == expected
                    or expected in normalized_candidate
                )
                for expected in expected_values
            )

        if not contract_saved_confirmed and supervisor_section is not None:
            contract_saved_confirmed = True

        return {
            "save_clicked": True,
            "success_dialog_found": True,
            "success_dialog_accepted": accepted,
            "contract_saved_confirmed": contract_saved_confirmed,
            "supervisor_section_found": supervisor_section is not None,
        }

    def _link_availability_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        expected_cdp: str,
    ) -> dict[str, bool]:
        """Busca, vincula y confirma una disponibilidad presupuestal."""

        flags = {
            "availability_search_written": False,
            "availability_result_found": False,
            "availability_result_matches": False,
            "availability_link_clicked": False,
            "availability_link_success_found": False,
            "availability_linked_row_confirmed": False,
            "continue_button_found": False,
            "continue_clicked": False,
            "budget_register_section_found": False,
        }
        expected = str(expected_cdp).strip()
        if not expected:
            raise PortalTimeoutError(
                "El número de CDP es obligatorio.",
                code="MISSING_CDP_CODE",
            )

        resolver.visible(
            "availability.section",
            timeout_seconds=self._timeout_seconds,
        )
        search = resolver.clickable(
            "availability.search_input",
            timeout_seconds=self._timeout_seconds,
        )
        self._scroll_into_view(driver, search)
        search.send_keys(Keys.CONTROL, "a")
        search.send_keys(Keys.BACKSPACE)
        search.send_keys(expected)
        search.send_keys(Keys.TAB)
        flags["availability_search_written"] = True

        try:
            row = waits.until(
                lambda current_driver: self._find_availability_row(
                    driver=current_driver,
                    expected_cdp=expected,
                    linked=False,
                ),
                timeout_seconds=max(25.0, self._timeout_seconds),
                message="No apareció el CDP esperado.",
            )
        except TimeoutException as error:
            raise PortalTimeoutError(
                f"El CDP {expected} no existe entre las disponibilidades.",
                code="AVAILABILITY_CDP_NOT_FOUND",
                metadata={"expected_cdp": expected},
            ) from error

        flags["availability_result_found"] = True
        flags["availability_result_matches"] = True

        try:
            link_button = row.find_element(
                By.CSS_SELECTOR,
                "button[title='Vincular']",
            )
        except Exception as error:
            raise PortalTimeoutError(
                "La fila del CDP no contiene el botón Vincular.",
                code="AVAILABILITY_LINK_BUTTON_NOT_FOUND",
                metadata={"expected_cdp": expected},
            ) from error

        click_errors: list[str] = []
        linked_row: WebElement | None = None
        success_found = False
        for mode in ("native", "actions", "javascript"):
            self._scroll_into_view(driver, link_button)
            try:
                self._perform_click(
                    driver=driver,
                    element=link_button,
                    mode=mode,
                )
            except WebDriverException as error:
                click_errors.append(f"{mode}: {type(error).__name__}")
                continue

            flags["availability_link_clicked"] = True
            success = resolver.optional_visible(
                "availability.link_success",
                timeout_seconds=min(4.0, self._timeout_seconds),
            )
            success_found = success is not None
            try:
                linked_row = waits.until(
                    lambda current_driver: self._find_availability_row(
                        driver=current_driver,
                        expected_cdp=expected,
                        linked=True,
                    ),
                    timeout_seconds=max(12.0, self._timeout_seconds),
                    message="El CDP no apareció en disponibilidades vinculadas.",
                )
            except TimeoutException:
                linked_row = None

            if linked_row is not None:
                break
            click_errors.append(f"{mode}: sin fila vinculada")

        if linked_row is None:
            raise PortalTimeoutError(
                f"El portal no confirmó la vinculación del CDP {expected}.",
                code="AVAILABILITY_LINK_CONFIRMATION_TIMEOUT",
                metadata={
                    "expected_cdp": expected,
                    "click_attempts": click_errors,
                },
            )

        flags["availability_link_success_found"] = bool(
            success_found or linked_row is not None
        )
        flags["availability_linked_row_confirmed"] = True

        continue_button = resolver.clickable(
            "availability.continue_button",
            timeout_seconds=self._timeout_seconds,
        )
        flags["continue_button_found"] = True
        continue_errors: list[str] = []
        for mode in ("native", "actions", "javascript"):
            self._scroll_into_view(driver, continue_button)
            try:
                self._perform_click(
                    driver=driver,
                    element=continue_button,
                    mode=mode,
                )
            except WebDriverException as error:
                continue_errors.append(
                    f"{mode}: {type(error).__name__}"
                )
                continue

            section = resolver.optional_visible(
                "budget_register.section",
                timeout_seconds=self._timeout_seconds,
            )
            if section is not None:
                flags["continue_clicked"] = True
                flags["budget_register_section_found"] = True
                return flags
            continue_errors.append(f"{mode}: sin registro presupuestal")

        raise PortalTimeoutError(
            "El CDP quedó vinculado, pero no se abrió Registro "
            "Presupuestal.",
            code="AVAILABILITY_CONTINUE_TIMEOUT",
            metadata={"click_attempts": continue_errors},
        )


    def _link_budget_register_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        contract: ContractData,
    ) -> dict[str, bool]:
        """Completa, valida y vincula el registro presupuestal."""

        register_number = str(
            contract.budget.budget_register_number or ""
        ).strip()
        if not register_number:
            raise PortalTimeoutError(
                "El número de registro presupuestal es obligatorio.",
                code="MISSING_BUDGET_REGISTER_NUMBER",
            )
        if contract.budget.gross_total <= Decimal("0"):
            raise PortalTimeoutError(
                "El Total Bruto debe ser mayor que cero.",
                code="INVALID_GROSS_TOTAL",
            )

        flags = {
            "budget_register_section_found": False,
            "budget_register_number_written": False,
            "budget_register_date_provided": (
                contract.budget.budget_register_date is not None
            ),
            "budget_register_date_written": False,
            "budget_register_availability_selected": False,
            "gross_total_written": False,
            "budget_register_validate_clicked": False,
            "budget_register_validation_confirmed": False,
            "budget_register_link_clicked": False,
            "budget_register_success_dialog_found": False,
            "budget_register_success_dialog_accepted": False,
            "budget_register_linked_confirmed": False,
            "additional_dates_section_found": False,
        }

        resolver.visible(
            "budget_register.section",
            timeout_seconds=self._timeout_seconds,
        )
        flags["budget_register_section_found"] = True

        self._write_text_field_by_key_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="budget_register.number_input",
            expected=register_number,
            code="BUDGET_REGISTER_NUMBER_WRITE_FAILED",
            label="No. Registro Presupuestal",
        )
        flags["budget_register_number_written"] = True

        register_date = contract.budget.budget_register_date
        if register_date is not None:
            expected_date = register_date.isoformat()
            self._write_date_field_by_key_and_confirm(
                driver=driver,
                waits=waits,
                resolver=resolver,
                key="budget_register.date_input",
                expected=expected_date,
                code="BUDGET_REGISTER_DATE_WRITE_FAILED",
                label="Fecha Registro Presupuestal",
            )
            flags["budget_register_date_written"] = True

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="budget_register.availability_select",
            expected=str(contract.budget.cdp_code),
            code="BUDGET_REGISTER_AVAILABILITY_SELECTION_FAILED",
            label="Disponibilidad Presupuestal",
            allow_decorated_value=True,
            alternative_clickable_key=None,
        )
        flags["budget_register_availability_selected"] = True

        self._write_currency_field_by_key_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="budget_register.gross_total_input",
            expected=contract.budget.gross_total,
            code="BUDGET_REGISTER_GROSS_TOTAL_WRITE_FAILED",
            label="Total Bruto",
        )
        flags["gross_total_written"] = True

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="budget_register.validate_button",
            target_key="budget_register.validation_success",
            code="BUDGET_REGISTER_VALIDATION_TIMEOUT",
            label="el botón Vincular del registro presupuestal",
        )
        flags["budget_register_validate_clicked"] = True
        flags["budget_register_validation_confirmed"] = True

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="budget_register.link_button",
            target_key="budget_register.link_success_dialog",
            code="BUDGET_REGISTER_LINK_DIALOG_TIMEOUT",
            label="el diálogo de vinculación del registro presupuestal",
        )
        flags["budget_register_link_clicked"] = True
        flags["budget_register_success_dialog_found"] = True

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="budget_register.link_success_accept",
            target_key="budget_register.linked",
            code="BUDGET_REGISTER_LINK_CONFIRMATION_TIMEOUT",
            label="la etapa de fechas adicionales",
        )
        flags["budget_register_success_dialog_accepted"] = True
        flags["budget_register_linked_confirmed"] = True
        flags["additional_dates_section_found"] = True
        return flags


    def _link_additional_dates_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        contract: ContractData,
    ) -> dict[str, bool]:
        """Completa o salta C9 y confirma la pantalla de anexos."""

        flags = {
            "additional_dates_section_found": False,
            "additional_dates_any_provided": any((
                contract.guarantee_approval_date is not None,
                contract.website_publication_date is not None,
                contract.secop_publication_date is not None,
            )),
            "guarantee_approval_date_provided": (
                contract.guarantee_approval_date is not None
            ),
            "guarantee_approval_date_written": False,
            "website_publication_date_provided": (
                contract.website_publication_date is not None
            ),
            "website_publication_date_written": False,
            "secop_publication_date_provided": (
                contract.secop_publication_date is not None
            ),
            "secop_publication_date_written": False,
            "additional_dates_validate_clicked": False,
            "additional_dates_validation_confirmed": False,
            "additional_dates_link_clicked": False,
            "additional_dates_success_dialog_found": False,
            "additional_dates_success_dialog_accepted": False,
            "additional_dates_skipped": False,
            "additional_dates_linked_confirmed": False,
            "file_reported_section_found": False,
        }

        resolver.visible(
            "additional_dates.section",
            timeout_seconds=self._timeout_seconds,
        )
        flags["additional_dates_section_found"] = True

        if not flags["additional_dates_any_provided"]:
            self._click_and_confirm_visible(
                driver=driver,
                resolver=resolver,
                click_key="additional_dates.skip_button",
                target_key="file_reported.section",
                code="ADDITIONAL_DATES_SKIP_TIMEOUT",
                label="la pantalla de archivos reportados",
            )
            flags["additional_dates_skipped"] = True
            flags["additional_dates_linked_confirmed"] = True
            flags["file_reported_section_found"] = True
            return flags

        date_specs = (
            (
                "additional_dates.guarantee_approval_date_input",
                contract.guarantee_approval_date,
                "guarantee_approval_date_written",
                "ADDITIONAL_DATES_GUARANTEE_DATE_WRITE_FAILED",
                "Fecha Aprobación Garantía Única",
            ),
            (
                "additional_dates.web_publication_date_input",
                contract.website_publication_date,
                "website_publication_date_written",
                "ADDITIONAL_DATES_WEB_DATE_WRITE_FAILED",
                "Fecha de Publicación Página Web",
            ),
            (
                "additional_dates.secop_publication_date_input",
                contract.secop_publication_date,
                "secop_publication_date_written",
                "ADDITIONAL_DATES_SECOP_DATE_WRITE_FAILED",
                "Publicación SECOP",
            ),
        )

        for key, value, flag_name, code, label in date_specs:
            if value is None:
                continue
            self._write_date_field_by_key_and_confirm(
                driver=driver,
                waits=waits,
                resolver=resolver,
                key=key,
                expected=value.isoformat(),
                code=code,
                label=label,
            )
            flags[flag_name] = True

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="additional_dates.validate_button",
            target_key="additional_dates.validation_success",
            code="ADDITIONAL_DATES_VALIDATION_TIMEOUT",
            label="el botón Vincular de fechas adicionales",
        )
        flags["additional_dates_validate_clicked"] = True
        flags["additional_dates_validation_confirmed"] = True

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="additional_dates.link_button",
            target_key="additional_dates.link_success_dialog",
            code="ADDITIONAL_DATES_LINK_DIALOG_TIMEOUT",
            label="el diálogo de vinculación de fechas adicionales",
        )
        flags["additional_dates_link_clicked"] = True
        flags["additional_dates_success_dialog_found"] = True

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="additional_dates.link_success_accept",
            target_key="file_reported.section",
            code="ADDITIONAL_DATES_LINK_CONFIRMATION_TIMEOUT",
            label="la pantalla de archivos reportados",
        )
        flags["additional_dates_success_dialog_accepted"] = True
        flags["additional_dates_linked_confirmed"] = True
        flags["file_reported_section_found"] = True
        return flags


    def _find_availability_row(
        self,
        *,
        driver: WebDriver,
        expected_cdp: str,
        linked: bool,
    ) -> WebElement | bool:
        heading = (
            "Disponibilidades Vinculadas al Contrato"
            if linked
            else "Seleccione la Disponibilidad a vincular al Contrato"
        )
        rows = driver.find_elements(
            By.XPATH,
            (
                f"//h6[normalize-space()='{heading}']"
                "/following::*[@role='grid'][1]"
                "//*[@role='row' and @data-id]"
            ),
        )
        for row in rows:
            try:
                cell = row.find_element(
                    By.CSS_SELECTOR,
                    (
                        "[role='gridcell']"
                        "[data-field='BUDGET_AVAILABILITY_IDENTIFIER']"
                    ),
                )
                observed = str(
                    cell.get_attribute("title")
                    or cell.text
                    or ""
                ).strip()
            except Exception:
                continue
            if self._cdp_matches(
                expected=expected_cdp,
                observed=observed,
            ):
                return row
        return False

    @staticmethod
    def _cdp_matches(*, expected: str, observed: str) -> bool:
        expected_normalized = re.sub(
            r"[^0-9A-Za-z]+",
            "",
            str(expected),
        ).casefold()
        observed_normalized = re.sub(
            r"[^0-9A-Za-z]+",
            "",
            str(observed),
        ).casefold()
        if not expected_normalized or not observed_normalized:
            return False
        if observed_normalized == expected_normalized:
            return True
        return (
            len(expected_normalized) >= 4
            and observed_normalized.startswith(expected_normalized)
        )

    def _link_supervisor_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        contract: ContractData,
        progress: dict[str, bool] | None = None,
    ) -> dict[str, bool]:
        """Vincula el supervisor interno y conserva el avance parcial."""

        supervisor_defaults = {
            "supervisor_dialog_opened": False,
            "supervisor_nature_selected": False,
            "supervisor_id_type_selected": False,
            "supervisor_document_written": False,
            "supervisor_result_found": False,
            "supervisor_selected": False,
            "supervisor_type_internal_confirmed": False,
            "supervisor_validate_clicked": False,
            "supervisor_validation_confirmed": False,
            "supervisor_link_clicked": False,
            "success_dialog_found": False,
            "success_dialog_accepted": False,
            "supervisor_linked_confirmed": False,
            "availability_section_found": False,
        }
        flags = progress if progress is not None else supervisor_defaults.copy()
        for key, value in supervisor_defaults.items():
            flags.setdefault(key, value)

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="supervisor.search_open",
            target_key="supervisor.dialog",
            code="SUPERVISOR_DIALOG_OPEN_TIMEOUT",
            label="la búsqueda de supervisor",
        )
        flags["supervisor_dialog_opened"] = True

        self._select_radio(
            driver=driver,
            resolver=resolver,
            key="supervisor.nature_person",
            code="SUPERVISOR_NATURE_SELECTION_FAILED",
            label="naturaleza Persona para el supervisor",
        )
        flags["supervisor_nature_selected"] = True

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="supervisor.id_type",
            expected="Cedula de Ciudadanía",
            code="SUPERVISOR_ID_TYPE_SELECTION_FAILED",
            label="Cédula de Ciudadanía",
            allow_decorated_value=True,
            alternative_clickable_key=None,
        )
        flags["supervisor_id_type_selected"] = True

        document_input = resolver.clickable(
            "supervisor.document_input",
            timeout_seconds=self._timeout_seconds,
        )
        self._write_and_confirm_wait(
            waits=waits,
            element=document_input,
            expected=contract.supervisor.document_number,
            code="SUPERVISOR_DOCUMENT_WRITE_FAILED",
            label="Cédula del supervisor",
        )
        flags["supervisor_document_written"] = True

        self._wait_for_supervisor_result_with_retries(
            driver=driver,
            resolver=resolver,
            expected_document=contract.supervisor.document_number,
        )
        flags["supervisor_result_found"] = True

        self._confirm_supervisor_selection_with_retries(
            driver=driver,
            waits=waits,
            resolver=resolver,
            expected_document=contract.supervisor.document_number,
        )
        flags["supervisor_selected"] = True

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="supervisor.type_input",
            expected="Interno",
            code="SUPERVISOR_TYPE_NOT_INTERNAL",
            label="tipo Interno del supervisor",
            allow_decorated_value=True,
            alternative_clickable_key=None,
        )
        flags["supervisor_type_internal_confirmed"] = True

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="supervisor.validate_button",
            target_key="supervisor.validation_success",
            code="SUPERVISOR_VALIDATION_TIMEOUT",
            label="la validación del supervisor",
        )
        flags["supervisor_validate_clicked"] = True
        flags["supervisor_validation_confirmed"] = True

        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="supervisor.link_button",
            target_key="supervisor.link_success_dialog",
            code="SUPERVISOR_LINK_DIALOG_TIMEOUT",
            label="el diálogo de vinculación del supervisor",
        )
        flags["supervisor_link_clicked"] = True
        flags["success_dialog_found"] = True

        errors: list[str] = []
        for mode in ("native", "actions", "javascript"):
            accept_button = resolver.clickable(
                "supervisor.link_success_accept",
                timeout_seconds=self._timeout_seconds,
            )
            self._scroll_into_view(driver, accept_button)
            try:
                self._perform_click(
                    driver=driver,
                    element=accept_button,
                    mode=mode,
                )
            except WebDriverException as error:
                errors.append(f"{mode}: {type(error).__name__}")
                continue

            linked = resolver.optional_visible(
                "supervisor.linked",
                timeout_seconds=self._timeout_seconds,
            )
            availability = resolver.optional_visible(
                "availability.section",
                timeout_seconds=min(3.0, self._timeout_seconds),
            )
            if linked is not None or availability is not None:
                flags["success_dialog_accepted"] = True
                flags["supervisor_linked_confirmed"] = True
                flags["availability_section_found"] = True
                return flags
            errors.append(f"{mode}: sin etapa de disponibilidad")

        raise PortalTimeoutError(
            "El supervisor fue vinculado, pero no se confirmó la etapa "
            "de disponibilidad presupuestal.",
            code="SUPERVISOR_LINK_ACCEPT_TIMEOUT",
            metadata={"click_attempts": errors},
        )

    def _click_supervisor_search_button(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        attempt: int,
    ) -> None:
        """Pulsa BUSCAR en el diálogo con fallbacks de interacción."""

        errors: list[str] = []
        for mode in ("native", "actions", "javascript"):
            button = resolver.clickable(
                "supervisor.search_button",
                timeout_seconds=self._timeout_seconds,
            )
            self._scroll_into_view(driver, button)
            try:
                self._perform_click(
                    driver=driver,
                    element=button,
                    mode=mode,
                )
                return
            except WebDriverException as error:
                errors.append(f"{mode}: {type(error).__name__}")

        raise PortalTimeoutError(
            "No fue posible pulsar Buscar en el diálogo del supervisor.",
            code="SUPERVISOR_SEARCH_CLICK_FAILED",
            metadata={
                "search_attempt": attempt,
                "click_attempts": errors,
            },
        )

    def _wait_for_supervisor_result_with_retries(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        expected_document: str,
    ) -> WebElement:
        """Pulsa Buscar y espera una coincidencia exacta del supervisor."""

        expected = str(expected_document).strip()
        attempt_timeout = max(25.0, self._timeout_seconds)
        attempts: list[str] = []
        observed_rows: list[str] = []

        for attempt in range(1, 4):
            self._click_supervisor_search_button(
                driver=driver,
                resolver=resolver,
                attempt=attempt,
            )
            try:
                row = resolver.visible(
                    "supervisor.result_row",
                    timeout_seconds=attempt_timeout,
                )
                row_text = str(getattr(row, "text", "") or "").strip()
                row_identifier = str(
                    row.get_attribute("data-id") or ""
                ).strip()
                observed = row_identifier or row_text
                if observed:
                    observed_rows.append(observed)

                if (
                    self._identity_contains(row_identifier, expected)
                    or self._identity_contains(row_text, expected)
                ):
                    return row

                attempts.append(
                    f"intento {attempt}: coincidencia distinta ({observed!r})"
                )
            except PortalTimeoutError:
                attempts.append(
                    f"intento {attempt}: lista sin coincidencias visibles"
                )

            if attempt >= 3:
                break

            try:
                document_input = resolver.clickable(
                    "supervisor.document_input",
                    timeout_seconds=min(5.0, self._timeout_seconds),
                )
                document_input.click()
                document_input.send_keys(Keys.CONTROL, "a")
                document_input.send_keys(Keys.BACKSPACE)
                document_input.send_keys(expected)
            except WebDriverException as error:
                attempts.append(
                    f"reactivación {attempt}: {type(error).__name__}"
                )

        if observed_rows:
            raise PortalTimeoutError(
                "La búsqueda devolvió coincidencias, pero ninguna corresponde "
                "a la cédula del supervisor.",
                code="SUPERVISOR_RESULT_MISMATCH",
                metadata={
                    "expected_document": expected,
                    "observed_rows": observed_rows,
                    "search_attempts": attempts,
                },
            )

        raise PortalTimeoutError(
            "No apareció una coincidencia para la cédula del supervisor "
            f"{expected} después de tres intentos de búsqueda automática.",
            code="SUPERVISOR_RESULT_NOT_FOUND",
            metadata={
                "expected_document": expected,
                "attempt_timeout_seconds": attempt_timeout,
                "search_attempts": attempts,
            },
        )

    def _confirm_supervisor_selection_with_retries(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        expected_document: str,
    ) -> None:
        selector = VerifiedSelectionInteractor(
            driver=driver,
            waits=waits,
            resolver=resolver,
            timeout_seconds=self._timeout_seconds,
        )
        selector.select(
            trigger_key="supervisor.select_button",
            postcondition=lambda _driver: self._resolved_identity_matches(
                resolver=resolver,
                key="supervisor.selected_identifier",
                expected=expected_document,
            ),
            error_code="SUPERVISOR_SELECTION_UNCONFIRMED",
            selection_label="Identificación del Supervisor",
        )

    def _resolved_identity_matches(
        self,
        *,
        resolver: ElementResolver,
        key: str,
        expected: str,
    ) -> bool:
        try:
            element = resolver.visible(
                key,
                timeout_seconds=min(0.75, self._timeout_seconds),
            )
            actual = str(
                element.get_attribute("value")
                or getattr(element, "text", "")
                or ""
            ).strip()
        except Exception:
            return False
        return self._identity_equals(actual, expected)

    def _validate_general_form_without_saving(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
    ) -> dict[str, bool]:
        """Pulsa Validar y confirma Guardar sin pulsarlo."""

        save_button = self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="general.final_validate_button",
            target_key="general.validation_success",
            code="GENERAL_VALIDATION_TIMEOUT",
            label="la validación general de C3-C4",
        )
        return {
            "general_validate_clicked": True,
            "general_validation_confirmed": True,
            "save_button_found": save_button is not None,
        }

    def _populate_general_data_draft(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        contract: ContractData,
    ) -> dict[str, bool]:
        """Completa C3 y confirma cada postcondición sin validar ni guardar."""

        flags = {
            "object_written": False,
            "signing_date_written": False,
            "starting_date_written": False,
            "amount_written": False,
            "amount_in_words_generated": False,
            "contract_term_written": False,
            "term_unit_days_selected": False,
            "process_type_selected": False,
            "procedure_selected": False,
            "contract_type_selected": False,
            "other_currency_no_selected": False,
        }

        object_input = resolver.visible(
            "general.object_description",
            timeout_seconds=self._timeout_seconds,
        )
        self._write_and_confirm_wait(
            waits=waits,
            element=object_input,
            expected=contract.object_description,
            code="GENERAL_OBJECT_WRITE_FAILED",
            label="Objeto del contrato",
        )
        flags["object_written"] = True

        self._write_date_and_confirm(
            waits=waits,
            element=resolver.visible(
                "general.signing_date",
                timeout_seconds=self._timeout_seconds,
            ),
            expected=contract.signing_date,
            code="GENERAL_SIGNING_DATE_WRITE_FAILED",
            label="Fecha de suscripción",
        )
        flags["signing_date_written"] = True

        self._write_date_and_confirm(
            waits=waits,
            element=resolver.visible(
                "general.starting_date",
                timeout_seconds=self._timeout_seconds,
            ),
            expected=contract.starting_date,
            code="GENERAL_STARTING_DATE_WRITE_FAILED",
            label="Fecha de inicio",
        )
        flags["starting_date_written"] = True

        self._write_currency_and_confirm(
            waits=waits,
            element=resolver.visible(
                "general.amount",
                timeout_seconds=self._timeout_seconds,
            ),
            expected=contract.amount,
            code="GENERAL_AMOUNT_WRITE_FAILED",
            label="Valor contractual",
        )
        flags["amount_written"] = True

        amount_words = resolver.visible(
            "general.amount_in_words",
            timeout_seconds=self._timeout_seconds,
        )
        try:
            waits.until(
                lambda _driver: bool(
                    str(amount_words.get_attribute("value") or "").strip()
                ),
                timeout_seconds=min(5.0, self._timeout_seconds),
            )
        except TimeoutException as error:
            raise PortalTimeoutError(
                "El portal no generó el valor contractual en letras.",
                code="GENERAL_AMOUNT_WORDS_UNCONFIRMED",
            ) from error
        flags["amount_in_words_generated"] = True

        term_input = resolver.visible(
            "general.contract_term",
            timeout_seconds=self._timeout_seconds,
        )
        self._write_and_confirm_wait(
            waits=waits,
            element=term_input,
            expected=str(contract.term_days),
            code="GENERAL_TERM_WRITE_FAILED",
            label="Plazo estimado",
        )
        flags["contract_term_written"] = True

        self._select_radio(
            driver=driver,
            resolver=resolver,
            key="general.term_unit_days",
            code="GENERAL_TERM_UNIT_SELECTION_FAILED",
            label="la unidad Días del plazo",
        )
        flags["term_unit_days_selected"] = True

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="general.process_type",
            expected=contract.process_type,
            code="GENERAL_PROCESS_TYPE_SELECTION_FAILED",
            label="Modalidad o Proceso",
        )
        flags["process_type_selected"] = True

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="general.typology",
            expected=contract.procedure,
            code="GENERAL_PROCEDURE_SELECTION_FAILED",
            label="Procedimiento o Causal",
            # El portal puede decorar la causal con el nombre o código de
            # la modalidad. La coincidencia sigue siendo semántica y se
            # limita al listbox perteneciente a este control.
            allow_decorated_value=True,
        )
        flags["procedure_selected"] = True

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="general.contract_type",
            expected=contract.contract_type,
            code="GENERAL_CONTRACT_TYPE_SELECTION_FAILED",
            label="Tipo de Contrato",
        )
        flags["contract_type_selected"] = True

        self._select_radio(
            driver=driver,
            resolver=resolver,
            key="general.other_currency_no",
            code="GENERAL_CURRENCY_SELECTION_FAILED",
            label="No en moneda extranjera",
        )
        flags["other_currency_no_selected"] = True

        return flags


    def _populate_general_completion_draft(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        contract: ContractData,
    ) -> dict[str, bool]:
        """Completa C4 sin pulsar la validación general ni Guardar."""

        flags = {
            "government_plan_selected": False,
            "budget_year_selected": False,
            "budget_item_selected": False,
            "budget_subsector_selected": False,
            "budget_link_clicked": False,
            "secop_yes_selected": False,
            "secop_url_written": False,
            "advance_no_selected": False,
            "commercial_trust_no_selected": False,
            "urgency_no_selected": False,
            "future_commitment_no_selected": False,
            "cooperation_contract_no_selected": False,
            "execution_department_selected": False,
            "execution_city_selected": False,
            "final_validate_button_found": False,
        }

        self._prepare_budget_catalog_chain(
            driver=driver,
            waits=waits,
            resolver=resolver,
            budget_year=str(contract.budget.year),
        )
        flags["government_plan_selected"] = True
        flags["budget_year_selected"] = True

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="general.budget_item",
            expected=contract.budget.item,
            code="GENERAL_BUDGET_ITEM_SELECTION_FAILED",
            label="Rubro Presupuestal",
            allow_decorated_value=True,
            alternative_clickable_key=None,
        )
        flags["budget_item_selected"] = True

        # El Sub-Sector depende del Rubro. React puede mantener el input
        # visible pero deshabilitado durante varios ciclos de renderizado.
        # No debe intentarse escribir hasta que el control sea interactivo.
        self._wait_for_dependent_autocomplete(
            resolver=resolver,
            key="general.budget_subsector",
            code="GENERAL_BUDGET_SUBSECTOR_NOT_READY",
            label="Sub-Sector",
            dependency_label="Rubro Presupuestal",
        )

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="general.budget_subsector",
            expected=contract.budget.subsector,
            code="GENERAL_BUDGET_SUBSECTOR_SELECTION_FAILED",
            label="Sub-Sector",
            allow_decorated_value=True,
            alternative_clickable_key=None,
        )
        flags["budget_subsector_selected"] = True

        budget_link = resolver.clickable(
            "general.budget_link_button",
            timeout_seconds=self._timeout_seconds,
        )
        self._scroll_into_view(driver, budget_link)
        self._click_with_fallbacks(driver=driver, element=budget_link)
        flags["budget_link_clicked"] = True

        self._select_radio(
            driver=driver,
            resolver=resolver,
            key="general.secop_yes",
            code="GENERAL_SECOP_SELECTION_FAILED",
            label="Sí en publicación SECOP",
        )
        flags["secop_yes_selected"] = True

        secop_url = resolver.visible(
            "general.secop_url",
            timeout_seconds=self._timeout_seconds,
        )
        self._write_and_confirm_wait(
            waits=waits,
            element=secop_url,
            expected=str(contract.secop_url),
            code="GENERAL_SECOP_URL_WRITE_FAILED",
            label="URL del contrato en SECOP",
        )
        flags["secop_url_written"] = True

        negative_flags = (
            (
                "general.advance_no",
                "GENERAL_ADVANCE_SELECTION_FAILED",
                "No en Anticipo",
                "advance_no_selected",
            ),
            (
                "general.commercial_trust_no",
                "GENERAL_TRUST_SELECTION_FAILED",
                "No en Fiducia Mercantil",
                "commercial_trust_no_selected",
            ),
            (
                "general.urgency_no",
                "GENERAL_URGENCY_SELECTION_FAILED",
                "No en Urgencia Manifiesta",
                "urgency_no_selected",
            ),
            (
                "general.future_commitment_no",
                "GENERAL_FUTURE_SELECTION_FAILED",
                "No en Vigencia Futura",
                "future_commitment_no_selected",
            ),
            (
                "general.cooperation_contract_no",
                "GENERAL_COOPERATION_SELECTION_FAILED",
                "No en Convenio",
                "cooperation_contract_no_selected",
            ),
        )
        for key, code, label, flag_name in negative_flags:
            self._select_radio(
                driver=driver,
                resolver=resolver,
                key=key,
                code=code,
                label=label,
            )
            flags[flag_name] = True

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="general.execution_department",
            expected=self._DEFAULT_EXECUTION_DEPARTMENT,
            code="GENERAL_EXECUTION_DEPARTMENT_SELECTION_FAILED",
            label="Departamento de Ejecución",
            allow_decorated_value=True,
            alternative_clickable_key=None,
        )
        flags["execution_department_selected"] = True

        self._wait_for_dependent_autocomplete(
            resolver=resolver,
            key="general.execution_city",
            code="GENERAL_EXECUTION_CITY_NOT_READY",
            label="Municipio de Ejecución",
            dependency_label="Departamento de Ejecución",
        )

        self._select_autocomplete_and_confirm(
            driver=driver,
            waits=waits,
            resolver=resolver,
            key="general.execution_city",
            expected=self._DEFAULT_EXECUTION_CITY,
            code="GENERAL_EXECUTION_CITY_SELECTION_FAILED",
            label="Municipio de Ejecución",
            allow_decorated_value=True,
        )
        flags["execution_city_selected"] = True

        resolver.clickable(
            "general.final_validate_button",
            timeout_seconds=self._timeout_seconds,
        )
        flags["final_validate_button_found"] = True

        return flags



    def _populate_header_draft(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        contract: ContractData,
    ) -> dict[str, bool]:
        """Completa C1-C2 y deja disponible Validar sin pulsarlo."""

        flags = {
            "record_type_selected": False,
            "contract_number_written": False,
            "contractor_dialog_opened": False,
            "contractor_nature_selected": False,
            "contractor_document_written": False,
            "contractor_result_found": False,
            "contractor_selected": False,
            "project_dialog_opened": False,
            "project_code_written": False,
            "project_result_found": False,
            "project_selected": False,
            "validate_button_found": False,
        }

        self._select_contract_record_type(
            driver=driver,
            resolver=resolver,
        )
        flags["record_type_selected"] = True

        contract_number = resolver.visible(
            "contract.header.contract_number",
            timeout_seconds=self._timeout_seconds,
        )
        self._write_and_confirm(
            element=contract_number,
            expected=contract.contract_number,
            code="CONTRACT_NUMBER_WRITE_FAILED",
            label="Número del contrato",
        )
        flags["contract_number_written"] = True

        flags.update(
            self._select_contractor_draft(
                driver=driver,
                waits=waits,
                resolver=resolver,
                contract=contract,
            )
        )
        flags.update(
            self._select_project_draft(
                driver=driver,
                waits=waits,
                resolver=resolver,
                project_code=contract.project_code,
            )
        )

        resolver.clickable(
            "contract.header.validate_button",
            timeout_seconds=self._timeout_seconds,
        )
        flags["validate_button_found"] = True
        return flags

    def _inspect_general_core_controls(
        self,
        resolver: ElementResolver,
    ) -> tuple[dict[str, bool], tuple[str, ...]]:
        flags: dict[str, bool] = {}
        missing: list[str] = []

        per_control_timeout = min(4.0, self._timeout_seconds)
        for flag_name, locator_key, label in self._GENERAL_CORE_CONTROL_SPECS:
            found = (
                resolver.optional_visible(
                    locator_key,
                    timeout_seconds=per_control_timeout,
                )
                is not None
            )
            flags[flag_name] = found
            if not found:
                missing.append(label)

        return flags, tuple(missing)

    def _select_contractor_draft(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        contract: ContractData,
    ) -> dict[str, bool]:
        flags = {
            "contractor_dialog_opened": False,
            "contractor_nature_selected": False,
            "contractor_document_written": False,
            "contractor_result_found": False,
            "contractor_selected": False,
        }
        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="contract.header.contractor_link",
            target_key="contractor.dialog",
            code="CONTRACTOR_DIALOG_OPEN_TIMEOUT",
            label="búsqueda de contratista",
        )
        flags["contractor_dialog_opened"] = True

        is_legal = contract.contractor.nature is ContractorNature.LEGAL_ENTITY
        nature_key = (
            "contractor.nature.legal"
            if is_legal
            else "contractor.nature.natural"
        )
        id_type_key = (
            "contractor.legal.id_type"
            if is_legal
            else "contractor.natural.id_type"
        )
        document_key = (
            "contractor.legal.document_input"
            if is_legal
            else "contractor.natural.document_input"
        )
        id_type_text = "NIT" if is_legal else "Cédula de Ciudadanía"

        self._select_radio(
            driver=driver,
            resolver=resolver,
            key=nature_key,
            code="CONTRACTOR_NATURE_SELECTION_TIMEOUT",
            label=("Persona Jurídica" if is_legal else "Persona Natural"),
        )
        flags["contractor_nature_selected"] = True

        id_type = resolver.visible(
            id_type_key,
            timeout_seconds=self._timeout_seconds,
        )
        self._select_autocomplete_value(
            element=id_type,
            value=id_type_text,
        )

        document = resolver.visible(
            document_key,
            timeout_seconds=self._timeout_seconds,
        )
        self._write_and_confirm(
            element=document,
            expected=contract.contractor.document_number,
            code="CONTRACTOR_DOCUMENT_WRITE_FAILED",
            label="Identificación del contratista",
            identity=True,
        )
        flags["contractor_document_written"] = True

        search = resolver.clickable(
            "contractor.search_button",
            timeout_seconds=self._timeout_seconds,
        )
        self._click_with_fallbacks(driver=driver, element=search)
        row = resolver.visible(
            "contractor.result_row",
            timeout_seconds=self._timeout_seconds,
        )
        if not self._identity_contains(
            getattr(row, "text", ""),
            contract.contractor.document_number,
        ):
            raise PortalTimeoutError(
                "La búsqueda devolvió un contratista distinto al solicitado.",
                code="CONTRACTOR_RESULT_MISMATCH",
            )
        flags["contractor_result_found"] = True

        self._confirm_contractor_selection_with_retries(
            driver=driver,
            waits=waits,
            resolver=resolver,
            expected_document=contract.contractor.document_number,
        )
        flags["contractor_selected"] = True
        return flags

    def _confirm_contractor_selection_with_retries(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        expected_document: str,
    ) -> None:
        self._confirm_dialog_selection(
            driver=driver,
            waits=waits,
            resolver=resolver,
            trigger_key="contractor.confirm_button",
            label="Identificación del Contratista",
            expected=expected_document,
            error_code="CONTRACTOR_SELECTION_UNCONFIRMED",
            identity=True,
        )

    def _select_project_draft(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        project_code: str,
    ) -> dict[str, bool]:
        flags = {
            "project_dialog_opened": False,
            "project_code_written": False,
            "project_result_found": False,
            "project_selected": False,
        }
        self._click_and_confirm_visible(
            driver=driver,
            resolver=resolver,
            click_key="contract.header.project_link",
            target_key="project.dialog",
            code="PROJECT_DIALOG_OPEN_TIMEOUT",
            label="búsqueda de proyecto",
        )
        flags["project_dialog_opened"] = True

        code_input = resolver.visible(
            "project.code_input",
            timeout_seconds=self._timeout_seconds,
        )
        self._write_and_confirm(
            element=code_input,
            expected=project_code,
            code="PROJECT_CODE_WRITE_FAILED",
            label="Código del proyecto",
        )
        flags["project_code_written"] = True

        search = resolver.clickable(
            "project.search_button",
            timeout_seconds=self._timeout_seconds,
        )
        self._click_with_fallbacks(driver=driver, element=search)
        row = resolver.visible(
            "project.result_row",
            timeout_seconds=self._timeout_seconds,
        )
        if self._normalize_text(project_code) not in self._normalize_text(
            getattr(row, "text", "")
        ):
            raise PortalTimeoutError(
                "La búsqueda devolvió un proyecto distinto al solicitado.",
                code="PROJECT_RESULT_MISMATCH",
            )
        flags["project_result_found"] = True

        self._confirm_project_selection_with_retries(
            driver=driver,
            waits=waits,
            resolver=resolver,
            expected_project_code=project_code,
        )
        flags["project_selected"] = True
        return flags

    def _confirm_project_selection_with_retries(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        expected_project_code: str,
    ) -> None:
        self._confirm_dialog_selection(
            driver=driver,
            waits=waits,
            resolver=resolver,
            trigger_key="project.confirm_button",
            label="Código del Proyecto",
            expected=expected_project_code,
            error_code="PROJECT_SELECTION_UNCONFIRMED",
            identity=False,
        )

    def _confirm_dialog_selection(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        trigger_key: str,
        label: str,
        expected: str,
        error_code: str,
        identity: bool = False,
    ) -> None:
        """Patrón común para contratista, proyecto y futuro supervisor."""

        selector = VerifiedSelectionInteractor(
            driver=driver,
            waits=waits,
            resolver=resolver,
            timeout_seconds=self._timeout_seconds,
        )
        selector.select(
            trigger_key=trigger_key,
            postcondition=lambda active_driver: (
                self._labeled_input_value_matches(
                    driver=active_driver,
                    label=label,
                    expected=expected,
                    identity=identity,
                )
            ),
            error_code=error_code,
            selection_label=label,
        )

    def _click_and_confirm_visible(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        click_key: str,
        target_key: str,
        code: str,
        label: str,
    ) -> WebElement:
        errors: list[str] = []
        for mode in ("native", "actions", "javascript"):
            element = resolver.clickable(
                click_key,
                timeout_seconds=self._timeout_seconds,
            )
            self._scroll_into_view(driver, element)
            try:
                self._perform_click(driver=driver, element=element, mode=mode)
            except WebDriverException as error:
                errors.append(f"{mode}: {type(error).__name__}")
                continue
            target = resolver.optional_visible(
                target_key,
                timeout_seconds=self._timeout_seconds,
            )
            if target is not None:
                return target
            errors.append(f"{mode}: sin postcondición visible")
        raise PortalTimeoutError(
            f"No fue posible abrir {label}.",
            code=code,
            metadata={"click_attempts": errors},
        )

    def _select_radio(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        key: str,
        code: str,
        label: str,
    ) -> None:
        errors: list[str] = []
        for mode in ("native", "actions", "javascript"):
            radio = resolver.presence(
                key,
                timeout_seconds=self._timeout_seconds,
            )
            self._scroll_into_view(driver, radio)
            try:
                self._perform_click(driver=driver, element=radio, mode=mode)
            except WebDriverException as error:
                errors.append(f"{mode}: {type(error).__name__}")
                continue
            if self._radio_checked(driver, radio):
                return
            errors.append(f"{mode}: radio no seleccionado")
        raise PortalTimeoutError(
            f"No fue posible seleccionar {label}.",
            code=code,
            metadata={"click_attempts": errors},
        )

    @staticmethod
    def _radio_checked(driver: WebDriver, element: WebElement) -> bool:
        try:
            return bool(element.is_selected())
        except Exception:
            try:
                return bool(
                    driver.execute_script(
                        "return arguments[0].checked === true;",
                        element,
                    )
                )
            except Exception:
                return False

    @staticmethod
    def _select_autocomplete_value(*, element: WebElement, value: str) -> None:
        element.click()
        element.clear()
        element.send_keys(value)
        element.send_keys(Keys.ARROW_DOWN)
        element.send_keys(Keys.ENTER)
        element.send_keys(Keys.TAB)

    def _write_text_field_by_key_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        key: str,
        expected: str,
        code: str,
        label: str,
    ) -> None:
        """Escribe y confirma un input React relocalizándolo tras cada render."""

        attempt_errors: list[str] = []
        expected_text = str(expected)

        for attempt in range(1, 4):
            try:
                element = resolver.clickable(
                    key,
                    timeout_seconds=self._timeout_seconds,
                )
                self._scroll_into_view(driver, element)
                element.clear()
                element.send_keys(expected_text)
                element.send_keys(Keys.TAB)
            except StaleElementReferenceException as error:
                attempt_errors.append(
                    f"intento {attempt}: stale durante escritura: {error}"
                )
                continue

            try:
                waits.until(
                    lambda _driver: self._resolved_text_field_matches(
                        resolver=resolver,
                        key=key,
                        expected=expected_text,
                    ),
                    timeout_seconds=min(5.0, self._timeout_seconds),
                )
                return
            except TimeoutException as error:
                attempt_errors.append(
                    f"intento {attempt}: valor no confirmado: {error}"
                )

        actual = self._resolved_field_text(
            resolver=resolver,
            key=key,
        )
        raise PortalTimeoutError(
            f"No fue posible confirmar el campo {label}.",
            code=code,
            metadata={
                "expected": expected_text,
                "actual": actual,
                "attempts": attempt_errors,
            },
        )

    def _write_date_field_by_key_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        key: str,
        expected: str,
        code: str,
        label: str,
    ) -> None:
        """Escribe una fecha React sin duplicarla durante los reintentos.

        Los datepickers de Gestión Transparente no siempre responden a
        ``WebElement.clear()``. Antes de escribir se comprueba si la fecha ya
        está presente. Cuando hace falta reemplazarla, se usa Ctrl+A,
        Backspace y Delete; después se despachan eventos input/change.
        """

        expected_text = str(expected).strip()
        attempt_errors: list[str] = []

        for attempt in range(1, 4):
            actual_before = self._resolved_field_text(
                resolver=resolver,
                key=key,
            )

            if self._date_field_matches(
                actual=actual_before,
                expected=expected_text,
            ):
                return

            try:
                element = resolver.clickable(
                    key,
                    timeout_seconds=self._timeout_seconds,
                )
                self._scroll_into_view(driver, element)

                element.send_keys(Keys.CONTROL, "a")
                element.send_keys(Keys.BACKSPACE)
                element.send_keys(Keys.DELETE)

                try:
                    driver.execute_script(
                        """
                        const input = arguments[0];
                        const descriptor = Object.getOwnPropertyDescriptor(
                            HTMLInputElement.prototype,
                            'value'
                        );
                        if (descriptor && descriptor.set) {
                            descriptor.set.call(input, '');
                        } else {
                            input.value = '';
                        }
                        input.dispatchEvent(
                            new Event('input', { bubbles: true })
                        );
                        input.dispatchEvent(
                            new Event('change', { bubbles: true })
                        );
                        """,
                        element,
                    )
                except WebDriverException:
                    # El borrado por teclado sigue siendo válido.
                    pass

                element = resolver.clickable(
                    key,
                    timeout_seconds=self._timeout_seconds,
                )
                element.send_keys(expected_text)
                element.send_keys(Keys.TAB)

            except StaleElementReferenceException as error:
                attempt_errors.append(
                    f"intento {attempt}: stale durante fecha: {error}"
                )
                continue

            try:
                waits.until(
                    lambda _driver: self._resolved_date_field_matches(
                        resolver=resolver,
                        key=key,
                        expected=expected_text,
                    ),
                    timeout_seconds=min(5.0, self._timeout_seconds),
                )
                return
            except TimeoutException as error:
                actual_after = self._resolved_field_text(
                    resolver=resolver,
                    key=key,
                )
                attempt_errors.append(
                    (
                        f"intento {attempt}: fecha no confirmada; "
                        f"actual={actual_after!r}: {error}"
                    )
                )

        actual = self._resolved_field_text(
            resolver=resolver,
            key=key,
        )
        raise PortalTimeoutError(
            f"No fue posible confirmar el campo {label}.",
            code=code,
            metadata={
                "expected": expected_text,
                "actual": actual,
                "attempts": attempt_errors,
            },
        )

    def _resolved_date_field_matches(
        self,
        *,
        resolver: ElementResolver,
        key: str,
        expected: str,
    ) -> bool:
        return self._date_field_matches(
            actual=self._resolved_field_text(
                resolver=resolver,
                key=key,
            ),
            expected=expected,
        )

    @classmethod
    def _date_field_matches(cls, *, actual: str, expected: str) -> bool:
        """Compara una única fecha y rechaza valores concatenados."""

        actual_date = cls._parse_portal_date(actual)
        expected_date = cls._parse_portal_date(expected)

        return (
            actual_date is not None
            and expected_date is not None
            and actual_date == expected_date
        )

    @staticmethod
    def _parse_portal_date(raw_value: str) -> date | None:
        text = str(raw_value or "").strip()
        if not text:
            return None

        for date_format in (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
        ):
            try:
                return datetime.strptime(text, date_format).date()
            except ValueError:
                continue

        return None


    def _write_currency_field_by_key_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        key: str,
        expected: Decimal,
        code: str,
        label: str,
    ) -> None:
        """Escribe moneda y confirma sobre una referencia React relocalizada."""

        expected_text = format(expected, "f")
        if "." in expected_text:
            expected_text = expected_text.rstrip("0").rstrip(".")

        attempt_errors: list[str] = []
        for attempt in range(1, 4):
            try:
                element = resolver.clickable(
                    key,
                    timeout_seconds=self._timeout_seconds,
                )
                self._scroll_into_view(driver, element)
                element.clear()
                element.send_keys(expected_text)
                element.send_keys(Keys.TAB)
            except StaleElementReferenceException as error:
                attempt_errors.append(
                    f"intento {attempt}: stale durante escritura: {error}"
                )
                continue

            try:
                waits.until(
                    lambda _driver: self._resolved_currency_field_matches(
                        resolver=resolver,
                        key=key,
                        expected=expected,
                    ),
                    timeout_seconds=min(5.0, self._timeout_seconds),
                )
                return
            except TimeoutException as error:
                attempt_errors.append(
                    f"intento {attempt}: moneda no confirmada: {error}"
                )

        actual = self._resolved_field_text(
            resolver=resolver,
            key=key,
        )
        raise PortalTimeoutError(
            f"No fue posible confirmar el campo {label}.",
            code=code,
            metadata={
                "expected": expected_text,
                "actual": actual,
                "attempts": attempt_errors,
            },
        )

    def _resolved_text_field_matches(
        self,
        *,
        resolver: ElementResolver,
        key: str,
        expected: str,
    ) -> bool:
        actual = self._resolved_field_text(
            resolver=resolver,
            key=key,
        )
        return self._semantic_text_equals(actual, expected)

    def _resolved_currency_field_matches(
        self,
        *,
        resolver: ElementResolver,
        key: str,
        expected: Decimal,
    ) -> bool:
        actual = self._resolved_field_text(
            resolver=resolver,
            key=key,
        )
        return self._currency_value_equals(actual, expected)

    def _resolved_field_text(
        self,
        *,
        resolver: ElementResolver,
        key: str,
    ) -> str:
        try:
            element = resolver.optional_visible(
                key,
                timeout_seconds=min(0.75, self._timeout_seconds),
            )
            if element is None:
                return ""
            return str(
                element.get_attribute("value")
                or element.text
                or ""
            ).strip()
        except (StaleElementReferenceException, WebDriverException):
            return ""

    def _write_and_confirm_wait(
        self,
        *,
        waits: SeleniumWaits,
        element: WebElement,
        expected: str,
        code: str,
        label: str,
    ) -> None:
        element.clear()
        element.send_keys(str(expected))
        element.send_keys(Keys.TAB)
        try:
            waits.until(
                lambda _driver: self._semantic_text_equals(
                    element.get_attribute("value") or element.text or "",
                    expected,
                ),
                timeout_seconds=min(5.0, self._timeout_seconds),
            )
        except TimeoutException as error:
            actual = element.get_attribute("value") or element.text or ""
            raise PortalTimeoutError(
                f"No fue posible confirmar el campo {label}.",
                code=code,
                metadata={"expected": str(expected), "actual": actual},
            ) from error

    def _write_date_and_confirm(
        self,
        *,
        waits: SeleniumWaits,
        element: WebElement,
        expected: date,
        code: str,
        label: str,
    ) -> None:
        expected_text = self._format_portal_date(expected)
        self._write_and_confirm_wait(
            waits=waits,
            element=element,
            expected=expected_text,
            code=code,
            label=label,
        )

    def _write_currency_and_confirm(
        self,
        *,
        waits: SeleniumWaits,
        element: WebElement,
        expected: Decimal,
        code: str,
        label: str,
    ) -> None:
        expected_text = format(expected, "f")
        if "." in expected_text:
            expected_text = expected_text.rstrip("0").rstrip(".")
        element.clear()
        element.send_keys(expected_text)
        element.send_keys(Keys.TAB)
        try:
            waits.until(
                lambda _driver: self._currency_value_equals(
                    element.get_attribute("value") or "",
                    expected,
                ),
                timeout_seconds=min(5.0, self._timeout_seconds),
            )
        except TimeoutException as error:
            actual = element.get_attribute("value") or ""
            raise PortalTimeoutError(
                f"No fue posible confirmar el campo {label}.",
                code=code,
                metadata={"expected": expected_text, "actual": actual},
            ) from error

    def _prepare_budget_catalog_chain(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        budget_year: str,
    ) -> None:
        """Estabiliza Plan de Gobierno -> Año -> Rubro antes de continuar."""

        attempt_errors: list[dict[str, object]] = []

        for attempt in range(1, 4):
            try:
                self._select_first_autocomplete_and_confirm(
                    driver=driver,
                    waits=waits,
                    resolver=resolver,
                    key="general.government_plan",
                    code="GENERAL_GOVERNMENT_PLAN_SELECTION_FAILED",
                    label="Plan de Gobierno",
                )

                self._wait_for_dependent_autocomplete(
                    resolver=resolver,
                    key="general.budget_year",
                    code="GENERAL_BUDGET_YEAR_NOT_READY",
                    label="Año del rubro presupuestal",
                    dependency_label="Plan de Gobierno",
                )

                self._select_autocomplete_and_confirm(
                    driver=driver,
                    waits=waits,
                    resolver=resolver,
                    key="general.budget_year",
                    expected=str(budget_year),
                    code="GENERAL_BUDGET_YEAR_SELECTION_FAILED",
                    label="Año del rubro presupuestal",
                )

                self._wait_for_dependent_autocomplete(
                    resolver=resolver,
                    key="general.budget_item",
                    code="GENERAL_BUDGET_ITEM_NOT_READY",
                    label="Rubro Presupuestal",
                    dependency_label="Año del rubro presupuestal",
                )
                return
            except PortalTimeoutError as error:
                attempt_errors.append(
                    {
                        "attempt": attempt,
                        "code": error.code,
                        "message": str(error),
                    }
                )

        raise PortalTimeoutError(
            (
                "No fue posible estabilizar la secuencia Plan de Gobierno, "
                "Año y Rubro Presupuestal."
            ),
            code="GENERAL_BUDGET_CATALOG_NOT_READY",
            metadata={"cascade_attempts": attempt_errors},
        )

    def _select_autocomplete_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        key: str,
        expected: str,
        code: str,
        label: str,
        allow_decorated_value: bool = False,
        alternative_clickable_key: str | None = None,
    ) -> None:
        """Selecciona un catálogo MUI y confirma su postcondición real.

        Los controles del portal mezclan inputs de Autocomplete y divs de
        Select. El teclado por sí solo es inestable: puede abrir la lista sin
        confirmar una opción. Por eso se prioriza el clic explícito sobre el
        elemento visible con role=option y se conserva el teclado únicamente
        como fallback.
        """

        errors: list[str] = []

        for attempt in range(1, 7):
            if self._autocomplete_selection_confirmed(
                resolver=resolver,
                key=key,
                expected=expected,
                allow_decorated_value=allow_decorated_value,
                alternative_clickable_key=alternative_clickable_key,
            ):
                return

            element = self._resolve_catalog_clickable_or_capture(
                driver=driver,
                resolver=resolver,
                key=key,
                expected=expected,
                code=code,
                label=label,
                attempts=errors,
            )
            self._scroll_into_view(driver, element)

            selected_option = ""
            try:
                self._open_catalog_control(
                    element=element,
                    expected=expected,
                )
                selected_option = (
                    self._click_visible_catalog_option(
                        driver=driver,
                        waits=waits,
                        expected=expected,
                        allow_decorated_value=allow_decorated_value,
                        control=element,
                    )
                    or ""
                )

                if not selected_option:
                    # Nunca confirme a ciegas la primera opción del catálogo.
                    # El fallback de teclado solo pulsa Enter cuando la opción
                    # activa pertenece al control objetivo y coincide con el
                    # valor esperado.
                    self._select_catalog_with_keyboard(
                        driver=driver,
                        resolver=resolver,
                        key=key,
                        expected=expected,
                        allow_decorated_value=allow_decorated_value,
                        control=element,
                    )
                else:
                    self._blur_catalog_control(
                        resolver=resolver,
                        key=key,
                    )
            except WebDriverException as error:
                errors.append(
                    f"intento {attempt}: {type(error).__name__}"
                )
                continue

            try:
                waits.until(
                    lambda _driver: self._autocomplete_selection_confirmed(
                        resolver=resolver,
                        key=key,
                        expected=expected,
                        allow_decorated_value=allow_decorated_value,
                        alternative_clickable_key=alternative_clickable_key,
                    ),
                    timeout_seconds=min(4.0, self._timeout_seconds),
                )
                return
            except TimeoutException:
                actual = self._resolved_autocomplete_value(
                    resolver=resolver,
                    key=key,
                )
                errors.append(
                    "intento "
                    f"{attempt}: opción={selected_option!r}, "
                    f"valor confirmado={actual!r}"
                )

        evidence_directory = self._capture_catalog_failure_evidence(
            driver=driver,
            resolver=resolver,
            key=key,
            expected=expected,
            code=code,
            label=label,
            attempts=errors,
        )

        raise PortalTimeoutError(
            f"No fue posible seleccionar {label}.",
            code=code,
            metadata={
                "expected": str(expected),
                "selection_attempts": errors,
                "alternative_clickable_key": alternative_clickable_key,
                "evidence_directory": evidence_directory,
            },
        )

    def _resolve_catalog_clickable_or_capture(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        key: str,
        expected: str,
        code: str,
        label: str,
        attempts: list[str],
    ) -> WebElement:
        """Resuelve un catálogo y captura evidencia si falla el localizador.

        El diagnóstico original solo se ejecutaba después de agotar los
        intentos de selección. Cuando ElementResolver fallaba antes de devolver
        el control, la excepción salía del helper y nunca se creaba la carpeta
        de evidencia. Esta envoltura cubre ese fallo temprano.
        """

        try:
            return resolver.clickable(
                key,
                timeout_seconds=self._timeout_seconds,
            )
        except PortalTimeoutError as error:
            resolver_error = (
                f"resolver: {error.code}: {str(error)}"
            )
            attempts.append(resolver_error)

            evidence_directory = (
                self._capture_catalog_failure_evidence(
                    driver=driver,
                    resolver=resolver,
                    key=key,
                    expected=expected,
                    code=code,
                    label=label,
                    attempts=attempts,
                )
            )

            raise PortalTimeoutError(
                (
                    f"No fue posible resolver el control {label}. "
                    "Se capturó evidencia del DOM antes de cerrar Chrome."
                ),
                code=code,
                metadata={
                    "expected": str(expected),
                    "resolver_error_code": error.code,
                    "resolver_error": str(error),
                    "selection_attempts": list(attempts),
                    "evidence_directory": evidence_directory,
                },
            ) from error


    def _capture_catalog_failure_evidence(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        key: str,
        expected: str,
        code: str,
        label: str,
        attempts: list[str],
        output_root: Path | None = None,
    ) -> str | None:
        """Guarda evidencia del estado real del catálogo después del fallo.

        Este diagnóstico no altera el flujo. Permite distinguir entre:
        - opción nunca encontrada;
        - opción encontrada pero no pulsada;
        - clic aceptado pero valor no reflejado;
        - localizador apuntando a un nodo distinto del input real;
        - lista MUI todavía abierta o reemplazada por React.
        """

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S_%fZ"
        )
        safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(key))
        root = output_root or (
            Path.cwd()
            / "artifacts"
            / "diagnostics"
            / "catalogs"
        )
        evidence_directory = root / f"{timestamp}_{safe_key}"

        try:
            evidence_directory.mkdir(parents=True, exist_ok=False)
        except Exception:
            return None

        payload: dict[str, object] = {
            "timestamp_utc": timestamp,
            "key": str(key),
            "label": str(label),
            "code": str(code),
            "expected": str(expected),
            "attempts": list(attempts),
            "current_url": str(
                getattr(driver, "current_url", "") or ""
            ),
            "control": {},
            "visible_options": [],
        }

        current: WebElement | None = None
        try:
            current = resolver.visible(
                key,
                timeout_seconds=min(1.0, self._timeout_seconds),
            )
            # Reabra el catálogo objetivo antes de fotografiarlo. Así la
            # evidencia conserva su propio aria-controls y no el listbox del
            # control siguiente que pudiera haber quedado enfocado.
            try:
                self._open_catalog_control(
                    element=current,
                    expected=expected,
                )
            except Exception:
                pass

            attributes = {}
            for attribute in (
                "id",
                "value",
                "textContent",
                "outerHTML",
                "class",
                "role",
                "aria-expanded",
                "aria-controls",
                "aria-activedescendant",
                "aria-invalid",
                "disabled",
                "readonly",
            ):
                try:
                    attributes[attribute] = (
                        current.get_attribute(attribute)
                    )
                except Exception as error:
                    attributes[attribute] = (
                        f"<{type(error).__name__}>"
                    )

            attributes["selenium_text"] = str(
                getattr(current, "text", "") or ""
            )
            attributes["tag_name"] = str(
                getattr(current, "tag_name", "") or ""
            )

            try:
                attributes["dom_value_property"] = (
                    driver.execute_script(
                        "return arguments[0].value ?? null;",
                        current,
                    )
                )
            except Exception as error:
                attributes["dom_value_property"] = (
                    f"<{type(error).__name__}>"
                )

            try:
                attributes["autocomplete_root_outer_html"] = (
                    driver.execute_script(
                        """
                        const element = arguments[0];
                        const root = element.closest(
                            '.MuiAutocomplete-root'
                        );
                        return root ? root.outerHTML : null;
                        """,
                        current,
                    )
                )
            except Exception as error:
                attributes["autocomplete_root_outer_html"] = (
                    f"<{type(error).__name__}>"
                )

            payload["control"] = attributes
        except Exception as error:
            payload["control_resolution_error"] = (
                f"{type(error).__name__}: {error}"
            )

        try:
            option_snapshots = []
            options = self._catalog_options_for_control(
                driver=driver,
                control=current,
            )
            for option in options:
                try:
                    option_snapshots.append(
                        {
                            "displayed": bool(option.is_displayed()),
                            "enabled": bool(option.is_enabled()),
                            "text": self._catalog_option_text(option),
                            "aria_selected": option.get_attribute(
                                "aria-selected"
                            ),
                            "id": option.get_attribute("id"),
                            "outer_html": option.get_attribute(
                                "outerHTML"
                            ),
                        }
                    )
                except Exception as error:
                    option_snapshots.append(
                        {
                            "inspection_error": (
                                f"{type(error).__name__}: {error}"
                            )
                        }
                    )
            payload["visible_options"] = option_snapshots
        except Exception as error:
            payload["options_resolution_error"] = (
                f"{type(error).__name__}: {error}"
            )

        try:
            (evidence_directory / "page_source.html").write_text(
                str(getattr(driver, "page_source", "") or ""),
                encoding="utf-8",
            )
        except Exception as error:
            payload["page_source_error"] = (
                f"{type(error).__name__}: {error}"
            )

        try:
            screenshot_path = evidence_directory / "screenshot.png"
            screenshot_saved = bool(
                driver.save_screenshot(str(screenshot_path))
            )
            payload["screenshot_saved"] = screenshot_saved
        except Exception as error:
            payload["screenshot_error"] = (
                f"{type(error).__name__}: {error}"
            )

        try:
            (evidence_directory / "catalog_state.json").write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
        except Exception:
            return str(evidence_directory)

        print(
            "[GT-CATALOG-DIAGNOSTIC] "
            f"{evidence_directory}",
            flush=True,
        )
        return str(evidence_directory)


    def _open_catalog_control(
        self,
        *,
        element: WebElement,
        expected: str,
    ) -> None:
        """Abre un Autocomplete o Select y escribe el filtro cuando aplica."""

        element.click()
        if not self._catalog_accepts_text(element):
            return

        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)
        element.send_keys(str(expected))

    @staticmethod
    def _catalog_accepts_text(element: WebElement) -> bool:
        tag_name = str(getattr(element, "tag_name", "") or "").casefold()
        if tag_name in {"input", "textarea"}:
            return True
        try:
            return (
                str(element.get_attribute("contenteditable") or "")
                .casefold()
                == "true"
            )
        except Exception:
            return False

    def _click_visible_catalog_option(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        expected: str | None,
        allow_decorated_value: bool,
        first_visible: bool = False,
        control: WebElement | None = None,
    ) -> str | None:
        """Pulsa una opción visible del listbox Material UI.

        La estructura role=listbox/role=option está confirmada por la
        evidencia DOM del portal y es compartida por Select y Autocomplete.
        """

        def locate_option(current_driver: WebDriver):
            try:
                options = self._catalog_options_for_control(
                    driver=current_driver,
                    control=control,
                )
            except Exception:
                return False

            for option in options:
                try:
                    if not option.is_displayed() or not option.is_enabled():
                        continue
                except Exception:
                    continue

                option_text = self._catalog_option_text(option)
                if not option_text:
                    continue

                if first_visible:
                    return option

                if expected is not None and self._catalog_option_matches(
                    actual=option_text,
                    expected=expected,
                    allow_decorated_value=allow_decorated_value,
                ):
                    return option
            return False

        click_errors: list[str] = []
        for mode in ("native", "actions", "javascript"):
            try:
                option = waits.until(
                    locate_option,
                    timeout_seconds=min(3.0, self._timeout_seconds),
                )
            except TimeoutException:
                return None

            option_text = self._catalog_option_text(option)
            self._scroll_into_view(driver, option)
            try:
                self._perform_click(
                    driver=driver,
                    element=option,
                    mode=mode,
                )
                return option_text
            except WebDriverException as error:
                click_errors.append(
                    f"{mode}: {type(error).__name__}"
                )

        if click_errors:
            raise WebDriverException(
                "No fue posible pulsar la opción del catálogo: "
                + "; ".join(click_errors)
            )
        return None

    @staticmethod
    def _catalog_options_for_control(
        *,
        driver: WebDriver,
        control: WebElement | None,
    ) -> list[WebElement]:
        """Devuelve únicamente las opciones del catálogo objetivo.

        Material UI renderiza sus listbox en un portal fuera del árbol del
        input. La relación confiable es ``aria-controls`` -> id del listbox.
        Buscar todas las opciones visibles de la página puede mezclar dos
        catálogos y seleccionar un valor en el control siguiente.
        """

        if control is None:
            return list(
                driver.find_elements(
                    By.CSS_SELECTOR,
                    "[role='listbox'] [role='option']",
                )
            )

        listbox_id = str(
            control.get_attribute("aria-controls") or ""
        ).strip()
        if not listbox_id:
            expanded = str(
                control.get_attribute("aria-expanded") or ""
            ).strip().casefold()
            if expanded != "true":
                return []
            # Compatibilidad con widgets que exponen el estado expandido pero
            # omiten aria-controls. Al exigir aria-expanded=true evitamos usar
            # el popup de un catálogo vecino cuando el objetivo está cerrado.
            return list(
                driver.find_elements(
                    By.CSS_SELECTOR,
                    "[role='listbox'] [role='option']",
                )
            )

        listboxes = driver.find_elements(By.ID, listbox_id)
        if not listboxes:
            return []

        return list(
            listboxes[0].find_elements(
                By.CSS_SELECTOR,
                "[role='option']",
            )
        )

    @classmethod
    def _catalog_option_matches(
        cls,
        *,
        actual: str,
        expected: str,
        allow_decorated_value: bool,
    ) -> bool:
        if cls._semantic_text_equals(actual, expected):
            return True
        if not allow_decorated_value:
            return False

        actual_normalized = cls._normalize_semantic_text(actual)
        expected_normalized = cls._normalize_semantic_text(expected)
        if len(actual_normalized) < 2 or len(expected_normalized) < 2:
            return False
        return (
            expected_normalized in actual_normalized
            or actual_normalized in expected_normalized
        )

    @staticmethod
    def _catalog_option_text(option: WebElement) -> str:
        candidates = (
            str(getattr(option, "text", "") or ""),
            str(option.get_attribute("textContent") or ""),
            str(option.get_attribute("data-value") or ""),
        )
        return next(
            (
                " ".join(candidate.strip().split())
                for candidate in candidates
                if candidate and candidate.strip()
            ),
            "",
        )

    def _select_catalog_with_keyboard(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        key: str,
        expected: str | None,
        allow_decorated_value: bool,
        first_visible: bool = False,
        control: WebElement | None = None,
    ) -> bool:
        """Confirma por teclado solo una opción activa verificable.

        El comportamiento anterior pulsaba ``ArrowDown`` y ``Enter`` aunque
        el filtro no hubiera encontrado el valor esperado. Eso podía elegir
        la primera causal disponible y desplazar el foco al Tipo de Contrato.
        """

        element = control or resolver.clickable(
            key,
            timeout_seconds=min(3.0, self._timeout_seconds),
        )
        element.send_keys(Keys.ARROW_DOWN)

        active_id = str(
            element.get_attribute("aria-activedescendant") or ""
        ).strip()
        if not active_id:
            return False

        active_options = driver.find_elements(By.ID, active_id)
        if not active_options:
            return False

        option_text = self._catalog_option_text(active_options[0])
        if not option_text:
            return False

        if not first_visible:
            if expected is None or not self._catalog_option_matches(
                actual=option_text,
                expected=expected,
                allow_decorated_value=allow_decorated_value,
            ):
                return False

        element.send_keys(Keys.ENTER)
        element.send_keys(Keys.TAB)
        return True

    def _blur_catalog_control(
        self,
        *,
        resolver: ElementResolver,
        key: str,
    ) -> None:
        try:
            current = resolver.clickable(
                key,
                timeout_seconds=min(2.0, self._timeout_seconds),
            )
            current.send_keys(Keys.TAB)
        except Exception:
            return

    def _autocomplete_selection_confirmed(
        self,
        *,
        resolver: ElementResolver,
        key: str,
        expected: str,
        allow_decorated_value: bool,
        alternative_clickable_key: str | None,
    ) -> bool:
        """Confirma exclusivamente el valor del control seleccionado.

        La disponibilidad de un control dependiente no demuestra que el
        catálogo anterior haya sido seleccionado. En Gestión Transparente,
        Sub-Sector, Vincular y Municipio pueden aparecer interactivos aunque
        Rubro, Sub-Sector o Departamento continúen vacíos. Las dependencias se
        esperan por separado después de confirmar el valor real.
        """

        return self._resolved_autocomplete_matches(
            resolver=resolver,
            key=key,
            expected=expected,
            allow_decorated_value=allow_decorated_value,
        )

    def _resolved_clickable_available(
        self,
        *,
        resolver: ElementResolver,
        key: str,
    ) -> bool:
        try:
            resolver.clickable(
                key,
                timeout_seconds=min(0.75, self._timeout_seconds),
            )
            return True
        except Exception:
            return False

    def _wait_for_dependent_autocomplete(
        self,
        *,
        resolver: ElementResolver,
        key: str,
        code: str,
        label: str,
        dependency_label: str,
    ) -> WebElement:
        try:
            return resolver.clickable(
                key,
                timeout_seconds=self._timeout_seconds,
            )
        except Exception as error:
            raise PortalTimeoutError(
                f"{label} no se habilitó después de seleccionar "
                f"{dependency_label}.",
                code=code,
                metadata={
                    "dependent_key": key,
                    "dependency": dependency_label,
                },
            ) from error

    def _resolved_autocomplete_matches(
        self,
        *,
        resolver: ElementResolver,
        key: str,
        expected: str,
        allow_decorated_value: bool,
    ) -> bool:
        actual = self._resolved_autocomplete_value(
            resolver=resolver,
            key=key,
        )
        if not actual:
            return False
        if self._semantic_text_equals(actual, expected):
            return True
        if not allow_decorated_value:
            return False

        actual_normalized = self._normalize_semantic_text(actual)
        expected_normalized = self._normalize_semantic_text(expected)
        if len(actual_normalized) < 3 or len(expected_normalized) < 3:
            return False
        return (
            expected_normalized in actual_normalized
            or actual_normalized in expected_normalized
        )

    def _resolved_autocomplete_value(
        self,
        *,
        resolver: ElementResolver,
        key: str,
    ) -> str:
        try:
            current = resolver.visible(
                key,
                timeout_seconds=min(0.75, self._timeout_seconds),
            )
            candidates = (
                str(current.get_attribute("value") or ""),
                str(getattr(current, "text", "") or ""),
                str(current.get_attribute("textContent") or ""),
                str(current.get_attribute("data-value") or ""),
            )
            return next(
                (
                    " ".join(candidate.strip().split())
                    for candidate in candidates
                    if candidate and candidate.strip()
                ),
                "",
            )
        except Exception:
            return ""

    def _select_first_autocomplete_and_confirm(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        key: str,
        code: str,
        label: str,
    ) -> str:
        errors: list[str] = []

        for attempt in range(1, 7):
            existing = self._resolved_autocomplete_value(
                resolver=resolver,
                key=key,
            )
            if existing:
                return existing

            element = self._resolve_catalog_clickable_or_capture(
                driver=driver,
                resolver=resolver,
                key=key,
                expected="<primera opción visible>",
                code=code,
                label=label,
                attempts=errors,
            )
            self._scroll_into_view(driver, element)

            selected_option = ""
            try:
                element.click()
                if self._catalog_accepts_text(element):
                    element.send_keys(Keys.CONTROL, "a")
                    element.send_keys(Keys.BACKSPACE)

                selected_option = (
                    self._click_visible_catalog_option(
                        driver=driver,
                        waits=waits,
                        expected=None,
                        allow_decorated_value=True,
                        first_visible=True,
                        control=element,
                    )
                    or ""
                )
                if not selected_option:
                    self._select_catalog_with_keyboard(
                        driver=driver,
                        resolver=resolver,
                        key=key,
                        expected=None,
                        allow_decorated_value=True,
                        first_visible=True,
                        control=element,
                    )
                else:
                    self._blur_catalog_control(
                        resolver=resolver,
                        key=key,
                    )
            except WebDriverException as error:
                errors.append(
                    f"intento {attempt}: {type(error).__name__}"
                )
                continue

            try:
                waits.until(
                    lambda _driver: bool(
                        self._resolved_autocomplete_value(
                            resolver=resolver,
                            key=key,
                        )
                    ),
                    timeout_seconds=min(3.0, self._timeout_seconds),
                )
                return self._resolved_autocomplete_value(
                    resolver=resolver,
                    key=key,
                )
            except TimeoutException:
                if selected_option:
                    return selected_option
                errors.append(
                    f"intento {attempt}: opción no confirmada"
                )

        raise PortalTimeoutError(
            f"No fue posible seleccionar {label}.",
            code=code,
            metadata={"selection_attempts": errors},
        )

    @staticmethod
    def _format_portal_date(value: date) -> str:
        return value.strftime("%d/%m/%Y")

    @classmethod
    def _semantic_text_equals(cls, first: object, second: object) -> bool:
        return cls._normalize_semantic_text(first) == cls._normalize_semantic_text(
            second
        )

    @staticmethod
    def _normalize_semantic_text(value: object) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value).casefold())
        without_marks = "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )
        return " ".join(without_marks.strip().split())

    @classmethod
    def _currency_value_equals(
        cls,
        actual: object,
        expected: Decimal,
    ) -> bool:
        return expected in cls._currency_candidates(actual)

    @staticmethod
    def _currency_candidates(value: object) -> set[Decimal]:
        raw = re.sub(r"[^0-9,.-]", "", str(value).strip())
        if not raw or raw in {"-", ".", ","}:
            return set()

        candidates: set[Decimal] = set()
        representations = {raw}
        representations.add(raw.replace(".", "").replace(",", "."))
        representations.add(raw.replace(",", ""))
        representations.add(raw.replace(".", ""))
        representations.add(raw.replace(",", "."))

        for representation in representations:
            if representation.count(".") > 1:
                continue
            try:
                candidates.add(Decimal(representation))
            except InvalidOperation:
                continue
        return candidates


    def _write_and_confirm(
        self,
        *,
        element: WebElement,
        expected: str,
        code: str,
        label: str,
        identity: bool = False,
    ) -> None:
        element.clear()
        element.send_keys(str(expected))
        element.send_keys(Keys.TAB)
        actual = element.get_attribute("value") or ""
        matches = (
            self._identity_equals(actual, expected)
            if identity
            else self._normalize_text(actual) == self._normalize_text(expected)
        )
        if not matches:
            raise PortalTimeoutError(
                f"No fue posible confirmar el campo {label}.",
                code=code,
                metadata={"expected": str(expected), "actual": actual},
            )

    def _wait_labeled_input_value(
        self,
        *,
        waits: SeleniumWaits,
        label: str,
        expected: str,
        code: str,
        identity: bool = False,
        timeout_seconds: float | None = None,
    ) -> None:
        try:
            waits.until(
                lambda driver: self._labeled_input_value_matches(
                    driver=driver,
                    label=label,
                    expected=expected,
                    identity=identity,
                ),
                timeout_seconds=(
                    self._timeout_seconds
                    if timeout_seconds is None
                    else float(timeout_seconds)
                ),
            )
        except TimeoutException as error:
            raise PortalTimeoutError(
                f"No fue posible confirmar la selección de {label}.",
                code=code,
            ) from error

    def _labeled_input_value_matches(
        self,
        *,
        driver: WebDriver,
        label: str,
        expected: str,
        identity: bool = False,
    ) -> bool:
        xpath = (
            f"//label[normalize-space()={self._xpath_literal(label)}]"
            "/following::input[1]"
        )
        try:
            element = driver.find_element(By.XPATH, xpath)
            actual = element.get_attribute("value") or ""
        except Exception:
            return False
        if identity:
            return self._identity_equals(actual, expected)
        return self._normalize_text(actual) == self._normalize_text(expected)

    def _click_with_fallbacks(
        self,
        *,
        driver: WebDriver,
        element: WebElement,
    ) -> None:
        errors: list[str] = []
        for mode in ("native", "actions", "javascript"):
            try:
                self._perform_click(driver=driver, element=element, mode=mode)
                return
            except WebDriverException as error:
                errors.append(f"{mode}: {type(error).__name__}")
        raise PortalTimeoutError(
            "No fue posible accionar el control esperado.",
            code="CONTROL_CLICK_FAILED",
            metadata={"click_attempts": errors},
        )

    @staticmethod
    def _normalize_text(value: object) -> str:
        return " ".join(str(value).strip().casefold().split())

    @staticmethod
    def _normalize_identity(value: object) -> str:
        return "".join(
            character
            for character in str(value).casefold()
            if character.isalnum()
        )

    def _identity_equals(self, first: object, second: object) -> bool:
        return self._normalize_identity(first) == self._normalize_identity(second)

    def _identity_contains(self, haystack: object, needle: object) -> bool:
        return self._normalize_identity(needle) in self._normalize_identity(haystack)

    @staticmethod
    def _xpath_literal(value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        return "concat(" + ", \"'\", ".join(
            f"'{part}'" for part in parts
        ) + ")"

    def _open_assistant_form(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
    ) -> WebElement:
        """Abre el asistente y espera la pantalla contractual completa."""

        already_visible = resolver.optional_visible(
            "assistant.container",
            timeout_seconds=min(2.0, self._timeout_seconds),
        )
        if already_visible is not None:
            return already_visible

        errors: list[str] = []
        for click_mode in ("native", "actions", "javascript"):
            access = resolver.clickable(
                "assistant.open",
                timeout_seconds=self._timeout_seconds,
            )
            self._scroll_into_view(driver, access)

            try:
                self._perform_click(
                    driver=driver,
                    element=access,
                    mode=click_mode,
                )
            except WebDriverException as error:
                errors.append(f"{click_mode}: {type(error).__name__}")
                continue

            container = resolver.optional_visible(
                "assistant.container",
                timeout_seconds=self._timeout_seconds,
            )
            if container is not None:
                return container

            errors.append(f"{click_mode}: formulario no visible")

        raise PortalTimeoutError(
            "No fue posible abrir el Asistente de Contratación y confirmar "
            "la pantalla del nuevo contrato.",
            code="ASSISTANT_OPEN_TIMEOUT",
            metadata={
                "toggle_key": "assistant.open",
                "target_key": "assistant.container",
                "click_attempts": errors,
            },
        )

    def _select_contract_record_type(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
    ) -> WebElement:
        """Selecciona Contrato y confirma que se renderice su cabecera.

        Gestión Transparente muestra inicialmente únicamente los radios
        Contrato y Factura. Los controles contractuales dependientes se
        montan después de pulsar Contrato, por lo que comprobarlos antes
        produciría un falso ASSISTANT_FORM_INCOMPLETE.
        """

        errors: list[str] = []
        target_wait = min(
            max(4.0, self._timeout_seconds / 2),
            self._timeout_seconds,
        )

        # Se pulsa siempre: un radio ya seleccionado no se desmarca y este
        # gesto vuelve determinista el montaje del formulario en React.
        for click_mode in ("native", "actions", "javascript"):
            radio = resolver.presence(
                "contract.header.record_type_contract",
                timeout_seconds=self._timeout_seconds,
            )
            self._scroll_into_view(driver, radio)

            try:
                self._perform_click(
                    driver=driver,
                    element=radio,
                    mode=click_mode,
                )
            except WebDriverException as error:
                errors.append(f"{click_mode}: {type(error).__name__}")
                continue

            contract_number = resolver.optional_visible(
                "contract.header.contract_number",
                timeout_seconds=target_wait,
            )
            if contract_number is not None:
                return contract_number

            errors.append(
                f"{click_mode}: Número del contrato no visible"
            )

        raise PortalTimeoutError(
            "Se encontró el radio Contrato, pero no fue posible activarlo "
            "ni confirmar la aparición de la cabecera contractual.",
            code="CONTRACT_RECORD_TYPE_SELECTION_TIMEOUT",
            metadata={
                "toggle_key": "contract.header.record_type_contract",
                "target_key": "contract.header.contract_number",
                "click_attempts": errors,
            },
        )

    def _inspect_header_controls(
        self,
        resolver: ElementResolver,
    ) -> tuple[dict[str, bool], tuple[str, ...]]:
        """Comprueba controles sin hacer clic ni escribir en el formulario."""

        timeout = min(
            8.0,
            max(2.0, self._timeout_seconds / 4),
        )
        flags: dict[str, bool] = {}
        missing: list[str] = []

        for flag_name, key, condition, label in self._HEADER_CONTROL_SPECS:
            try:
                resolver.resolve(
                    key,
                    condition=condition,
                    timeout_seconds=timeout,
                    capture_diagnostics=False,
                )
            except PortalTimeoutError:
                flags[flag_name] = False
                missing.append(label)
            else:
                flags[flag_name] = True

        return flags, tuple(missing)

    def _ensure_target_visible(
        self,
        *,
        driver: WebDriver,
        resolver: ElementResolver,
        toggle_key: str,
        target_key: str,
        step_code: str,
        step_label: str,
    ) -> WebElement:
        """Devuelve el siguiente nivel visible y evita colapsar menús abiertos."""

        already_visible = resolver.optional_visible(
            target_key,
            timeout_seconds=min(2.0, self._timeout_seconds),
        )
        if already_visible is not None:
            return already_visible

        errors: list[str] = []
        target_wait = min(
            max(3.0, self._timeout_seconds / 3),
            self._timeout_seconds,
        )

        for click_mode in ("native", "actions", "javascript"):
            toggle = resolver.clickable(
                toggle_key,
                timeout_seconds=self._timeout_seconds,
            )
            self._scroll_into_view(driver, toggle)

            try:
                self._perform_click(
                    driver=driver,
                    element=toggle,
                    mode=click_mode,
                )
            except WebDriverException as error:
                errors.append(f"{click_mode}: {type(error).__name__}")
                continue

            target = resolver.optional_visible(
                target_key,
                timeout_seconds=target_wait,
            )
            if target is not None:
                return target

            errors.append(f"{click_mode}: sin postcondición visible")

        raise PortalTimeoutError(
            f"No fue posible desplegar el menú '{step_label}' y confirmar "
            "su siguiente nivel.",
            code=step_code,
            metadata={
                "toggle_key": toggle_key,
                "target_key": target_key,
                "click_attempts": errors,
            },
        )

    @staticmethod
    def _scroll_into_view(
        driver: WebDriver,
        element: WebElement,
    ) -> None:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                element,
            )
        except WebDriverException:
            return

    @staticmethod
    def _perform_click(
        *,
        driver: WebDriver,
        element: WebElement,
        mode: str,
    ) -> None:
        if mode == "native":
            element.click()
            return

        if mode == "actions":
            ActionChains(driver).move_to_element(element).click().perform()
            return

        if mode == "javascript":
            driver.execute_script("arguments[0].click();", element)
            return

        raise ValueError(f"Modo de clic no soportado: {mode}.")
