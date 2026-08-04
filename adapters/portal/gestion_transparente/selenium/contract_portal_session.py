from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver

from adapters.portal.gestion_transparente.selenium.browser_session import (
    BrowserSession,
)
from adapters.portal.gestion_transparente.selenium.diagnostics import (
    BrowserDiagnostics,
)
from adapters.portal.gestion_transparente.selenium.driver_factory import (
    BrowserSettings,
    DriverFactory,
    WebDriverFactory,
)
from adapters.portal.gestion_transparente.selenium.element_resolver import (
    ElementResolver,
)
from adapters.portal.gestion_transparente.selenium.gestion_transparente_portal import (
    GestionTransparentePortal,
)
from adapters.portal.gestion_transparente.selenium.waits import SeleniumWaits
from application.dto import (
    PortalStepVerification,
    PortalVerificationStatus,
)
from application.ports.contract_portal_session import (
    OpenedContractPortalSession,
)
from application.ports.credential_cipher import CredentialCipher
from application.ports.portal_credential_repository import (
    PortalCredentialRepository,
)
from domain.enums import ContractStep
from domain.errors import (
    PortalAutomationError,
    PortalTimeoutError,
    PortalValidationError,
)
from domain.errors.portal_credential_errors import (
    PortalCredentialEncryptionError,
    PortalCredentialsNotConfiguredError,
)
from domain.models import ContractData


class ContractPortalSessionBusyError(RuntimeError):
    """Ya existe una sesión contractual activa en este proceso."""


class SeleniumContractPortalSessionFactory:
    """Crea una sesión GT autenticada compartida por todo el contrato."""

    PROFILE = "v2026_07"

    def __init__(
        self,
        *,
        login_url: str,
        credentials: PortalCredentialRepository,
        cipher: CredentialCipher,
        headless: bool = False,
        timeout_seconds: float = 25.0,
        driver_path: Path | None = None,
        chrome_binary: Path | None = None,
        factory: WebDriverFactory | None = None,
        registry_builder: Callable[[], Any] | None = None,
        diagnostics_directory: str | Path | None = (
            Path("logs") / "diagnostics" / "contract_execution"
        ),
    ) -> None:
        normalized_url = str(login_url).strip()
        if not normalized_url:
            raise ValueError("La URL de inicio de sesión es obligatoria.")
        if timeout_seconds <= 0:
            raise ValueError("El timeout debe ser mayor que cero.")

        self._login_url = normalized_url
        self._credentials = credentials
        self._cipher = cipher
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
        self._registry_builder = (
            registry_builder or self._build_default_registry
        )
        self._diagnostics_directory = (
            Path(diagnostics_directory)
            if diagnostics_directory is not None
            else None
        )
        self._lock = Lock()

    @property
    def profile(self) -> str:
        return self.PROFILE

    @contextmanager
    def open(
        self,
        *,
        dependency: str,
    ) -> Iterator[OpenedContractPortalSession]:
        normalized_dependency = " ".join(str(dependency).split())
        if not normalized_dependency:
            raise ValueError("La dependencia es obligatoria.")

        if not self._lock.acquire(blocking=False):
            raise ContractPortalSessionBusyError(
                "Ya existe una ejecución contractual con navegador activo."
            )

        try:
            credential = self._credentials.find_by_dependency(
                normalized_dependency
            )
            if credential is None:
                raise PortalCredentialsNotConfiguredError(
                    normalized_dependency
                )

            password = self._cipher.decrypt(
                credential.encrypted_password
            )
            if not str(password).strip():
                raise PortalCredentialEncryptionError(
                    "La contraseña descifrada del portal está vacía."
                )

            with BrowserSession(self._factory) as browser:
                browser.navigate(self._login_url)
                waits = SeleniumWaits(
                    browser.driver,
                    default_timeout_seconds=self._timeout_seconds,
                )
                diagnostics = (
                    BrowserDiagnostics(
                        browser.driver,
                        self._diagnostics_directory,
                    )
                    if self._diagnostics_directory is not None
                    else None
                )
                resolver = ElementResolver(
                    registry=self._registry_builder(),
                    waits=waits,
                    diagnostics=diagnostics,
                )

                try:
                    self._authenticate(
                        resolver=resolver,
                        username=credential.portal_username,
                        password=password,
                    )

                    from adapters.portal.gestion_transparente.batch_portal_probe import (
                        SeleniumBatchPortalProbe,
                    )

                    helper = SeleniumBatchPortalProbe(
                        login_url=self._login_url,
                        timeout_seconds=self._timeout_seconds,
                        factory=self._factory,
                    )
                    components = _SeleniumContractComponents(
                        driver=browser.driver,
                        waits=waits,
                        resolver=resolver,
                        helper=helper,
                        timeout_seconds=self._timeout_seconds,
                    )
                    portal = GestionTransparentePortal(
                        assistant=components,
                        header=components,
                        general_data=components,
                        supervisor=components,
                        availability=components,
                        budget_register=components,
                        additional_dates=components,
                        recovery=components,
                    )
                    yield OpenedContractPortalSession(
                        portal=portal,
                        profile=self.PROFILE,
                    )
                except BaseException as error:
                    self._capture_failure(
                        diagnostics=diagnostics,
                        dependency=normalized_dependency,
                        error=error,
                    )
                    raise
        finally:
            self._lock.release()


    @staticmethod
    def _capture_failure(
        *,
        diagnostics: BrowserDiagnostics | None,
        dependency: str,
        error: BaseException,
    ) -> None:
        """Captura evidencia sin sustituir la excepción original."""

        if diagnostics is None or isinstance(error, GeneratorExit):
            return

        try:
            evidence = diagnostics.capture(
                event="controlled_contract_execution_failure",
                metadata={"dependency": dependency},
                error=error,
            )
        except Exception:
            return

        if isinstance(error, PortalAutomationError):
            error.metadata.setdefault(
                "diagnostics",
                evidence.as_metadata(),
            )

    def _authenticate(
        self,
        *,
        resolver: ElementResolver,
        username: str,
        password: str,
    ) -> None:
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
        except PortalTimeoutError as error:
            if resolver.optional_visible(
                "portal.login.password",
                timeout_seconds=2.0,
            ) is not None:
                raise PortalValidationError(
                    "Gestión Transparente rechazó las credenciales.",
                    code="INVALID_CREDENTIALS",
                ) from error
            raise PortalTimeoutError(
                "El portal respondió, pero no fue posible confirmar "
                "el estado autenticado.",
                code="AUTHENTICATED_STATE_UNCONFIRMED",
            ) from error

    @staticmethod
    def _build_default_registry() -> Any:
        from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
            build_registry,
        )
        return build_registry()


class _SeleniumContractComponents:
    """Componentes semánticos GT sobre una única sesión WebDriver."""

    def __init__(
        self,
        *,
        driver: WebDriver,
        waits: SeleniumWaits,
        resolver: ElementResolver,
        helper: Any,
        timeout_seconds: float,
    ) -> None:
        self._driver = driver
        self._waits = waits
        self._resolver = resolver
        self._helper = helper
        self._timeout_seconds = float(timeout_seconds)

    def open(self, contract: ContractData) -> None:
        self._helper._ensure_target_visible(
            driver=self._driver,
            resolver=self._resolver,
            toggle_key="navigation.contracting_menu",
            target_key="navigation.enter_contract",
            step_code="CONTRACTING_MENU_EXPANSION_TIMEOUT",
            step_label="Contratación",
        )
        self._helper._ensure_target_visible(
            driver=self._driver,
            resolver=self._resolver,
            toggle_key="navigation.enter_contract",
            target_key="assistant.open",
            step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
            step_label="Ingresar Contrato",
        )
        self._helper._open_assistant_form(
            driver=self._driver,
            resolver=self._resolver,
        )

    def verify_open(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verify_view(
            step=ContractStep.ASSISTANT_OPENED,
            confirmed_keys=("assistant.container",),
            not_applied_keys=("assistant.open",),
            confirmed_message="El asistente contractual está abierto.",
            not_applied_message="El asistente contractual aún no está abierto.",
        )

    def complete_header(self, contract: ContractData) -> None:
        flags = self._helper._populate_header_draft(
            driver=self._driver,
            waits=self._waits,
            resolver=self._resolver,
            contract=contract,
        )
        self._require_flags(
            flags,
            (
                "record_type_selected",
                "contract_number_written",
                "contractor_selected",
                "project_selected",
                "validate_button_found",
            ),
            code="HEADER_DRAFT_INCOMPLETE",
            message="No se confirmaron todos los campos del encabezado.",
        )

    def verify_header_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        if self._visible("contract.header.validate_button"):
            number_input = self._resolver.optional_visible(
                "contract.header.contract_number",
                timeout_seconds=self._short_timeout,
            )
            observed = ""
            if number_input is not None:
                observed = str(
                    number_input.get_attribute("value")
                    or number_input.text
                    or ""
                )
            if self._identity(observed) == self._identity(
                contract.contract_number
            ):
                return self._confirmed(
                    ContractStep.HEADER_COMPLETED,
                    "El encabezado está completo y listo para validar.",
                )
            return self._ambiguous(
                ContractStep.HEADER_COMPLETED,
                "El número contractual visible no coincide con el esperado.",
                observed_contract_number=observed,
            )

        if self._visible("assistant.container"):
            return self._not_applied(
                ContractStep.HEADER_COMPLETED,
                "El asistente está abierto, pero el encabezado no está listo.",
            )
        return self._ambiguous(
            ContractStep.HEADER_COMPLETED,
            "No fue posible determinar el estado del encabezado.",
        )

    def validate_header(self, contract: ContractData) -> None:
        self._helper._click_and_confirm_visible(
            driver=self._driver,
            resolver=self._resolver,
            click_key="contract.header.validate_button",
            target_key="contract.header.validation_success",
            code="HEADER_VALIDATION_TIMEOUT",
            label="la validación del encabezado C1-C2",
        )

    def verify_header_validated(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verify_view(
            step=ContractStep.HEADER_VALIDATED,
            confirmed_keys=("general.object_description",),
            not_applied_keys=("contract.header.validate_button",),
            confirmed_message=(
                "El encabezado fue validado y se abrió la información general."
            ),
            not_applied_message="El encabezado todavía no ha sido validado.",
        )

    def complete_general_data(self, contract: ContractData) -> None:
        general_flags = self._helper._populate_general_data_draft(
            driver=self._driver,
            waits=self._waits,
            resolver=self._resolver,
            contract=contract,
        )
        self._require_all(
            general_flags,
            code="GENERAL_DATA_DRAFT_INCOMPLETE",
            message="No se confirmaron todos los datos generales C3.",
        )

        completion_flags = (
            self._helper._populate_general_completion_draft(
                driver=self._driver,
                waits=self._waits,
                resolver=self._resolver,
                contract=contract,
            )
        )
        self._require_all(
            completion_flags,
            code="GENERAL_COMPLETION_DRAFT_INCOMPLETE",
            message="No se confirmaron todos los datos complementarios C4.",
        )

        validation_flags = (
            self._helper._validate_general_form_without_saving(
                driver=self._driver,
                resolver=self._resolver,
            )
        )
        self._require_all(
            validation_flags,
            code="GENERAL_VALIDATION_INCOMPLETE",
            message="La validación general no dejó Guardar disponible.",
        )

    def verify_general_data_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verify_view(
            step=ContractStep.GENERAL_DATA_COMPLETED,
            confirmed_keys=("general.save_button",),
            not_applied_keys=(
                "general.object_description",
                "general.final_validate_button",
            ),
            confirmed_message=(
                "Los datos generales están validados y Guardar está disponible."
            ),
            not_applied_message=(
                "Los datos generales todavía no completaron su validación."
            ),
        )

    def save_contract(self, contract: ContractData) -> None:
        flags = self._helper._save_contract_and_confirm(
            driver=self._driver,
            resolver=self._resolver,
            contract=contract,
        )
        self._require_flags(
            flags,
            (
                "save_clicked",
                "success_dialog_found",
                "success_dialog_accepted",
                "contract_saved_confirmed",
                "supervisor_section_found",
            ),
            code="CONTRACT_SAVE_INCOMPLETE",
            message="El portal no confirmó completamente el guardado.",
        )

    def verify_contract_saved(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verify_view(
            step=ContractStep.CONTRACT_SAVED,
            confirmed_keys=("supervisor.section",),
            not_applied_keys=("general.save_button",),
            confirmed_message=(
                "El contrato fue guardado y se abrió la etapa del supervisor."
            ),
            not_applied_message="El contrato todavía no ha sido guardado.",
        )

    def link_supervisor(self, contract: ContractData) -> None:
        flags = self._helper._link_supervisor_and_confirm(
            driver=self._driver,
            waits=self._waits,
            resolver=self._resolver,
            contract=contract,
        )
        self._require_flags(
            flags,
            (
                "supervisor_linked_confirmed",
                "availability_section_found",
            ),
            code="SUPERVISOR_LINK_INCOMPLETE",
            message="El portal no confirmó la vinculación del supervisor.",
        )

    def verify_supervisor_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verify_view(
            step=ContractStep.SUPERVISOR_LINKED,
            confirmed_keys=(
                "availability.section",
                "supervisor.linked",
            ),
            not_applied_keys=("supervisor.section",),
            confirmed_message=(
                "El supervisor está vinculado y la disponibilidad está abierta."
            ),
            not_applied_message="El supervisor todavía no está vinculado.",
        )

    def link_availability(self, contract: ContractData) -> None:
        flags = self._helper._link_availability_and_confirm(
            driver=self._driver,
            waits=self._waits,
            resolver=self._resolver,
            expected_cdp=contract.budget.cdp_code,
        )
        self._require_flags(
            flags,
            (
                "availability_linked_row_confirmed",
                "continue_clicked",
                "budget_register_section_found",
            ),
            code="AVAILABILITY_LINK_INCOMPLETE",
            message="El portal no confirmó la vinculación del CDP.",
        )

    def verify_availability_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verify_view(
            step=ContractStep.AVAILABILITY_LINKED,
            confirmed_keys=("budget_register.section",),
            not_applied_keys=("availability.section",),
            confirmed_message=(
                "El CDP está vinculado y el registro presupuestal está abierto."
            ),
            not_applied_message="La disponibilidad todavía no está vinculada.",
        )

    def link_budget_register(self, contract: ContractData) -> None:
        flags = self._helper._link_budget_register_and_confirm(
            driver=self._driver,
            waits=self._waits,
            resolver=self._resolver,
            contract=contract,
        )
        self._require_flags(
            flags,
            (
                "budget_register_linked_confirmed",
                "additional_dates_section_found",
            ),
            code="BUDGET_REGISTER_LINK_INCOMPLETE",
            message=(
                "El portal no confirmó la vinculación del registro presupuestal."
            ),
        )

    def verify_budget_register_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verify_view(
            step=ContractStep.BUDGET_REGISTER_LINKED,
            confirmed_keys=(
                "additional_dates.section",
                "budget_register.linked",
            ),
            not_applied_keys=("budget_register.section",),
            confirmed_message=(
                "El registro presupuestal está vinculado y C9 está abierto."
            ),
            not_applied_message=(
                "El registro presupuestal todavía no está vinculado."
            ),
        )

    def link_additional_dates(self, contract: ContractData) -> None:
        flags = self._helper._link_additional_dates_and_confirm(
            driver=self._driver,
            waits=self._waits,
            resolver=self._resolver,
            contract=contract,
        )
        self._require_flags(
            flags,
            (
                "additional_dates_linked_confirmed",
                "file_reported_section_found",
            ),
            code="ADDITIONAL_DATES_LINK_INCOMPLETE",
            message=(
                "El portal no confirmó la finalización de fechas adicionales."
            ),
        )

    def verify_additional_dates_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verify_view(
            step=ContractStep.ADDITIONAL_DATES_LINKED,
            confirmed_keys=("file_reported.section",),
            not_applied_keys=("additional_dates.section",),
            confirmed_message=(
                "Las fechas adicionales finalizaron y se abrió Archivos "
                "Reportados."
            ),
            not_applied_message=(
                "La etapa de fechas adicionales todavía está pendiente."
            ),
        )

    def recover(self) -> None:
        self._driver.refresh()

    @property
    def _short_timeout(self) -> float:
        return min(3.0, self._timeout_seconds)

    def _visible(self, key: str) -> bool:
        return self._resolver.optional_visible(
            key,
            timeout_seconds=self._short_timeout,
        ) is not None

    def _verify_view(
        self,
        *,
        step: ContractStep,
        confirmed_keys: tuple[str, ...],
        not_applied_keys: tuple[str, ...],
        confirmed_message: str,
        not_applied_message: str,
    ) -> PortalStepVerification:
        for key in confirmed_keys:
            if self._visible(key):
                return self._confirmed(
                    step,
                    confirmed_message,
                    confirmed_locator=key,
                )
        for key in not_applied_keys:
            if self._visible(key):
                return self._not_applied(
                    step,
                    not_applied_message,
                    observed_locator=key,
                )
        return self._ambiguous(
            step,
            "El portal no mostró una postcondición concluyente para "
            f"{step.value}.",
            confirmed_candidates=confirmed_keys,
            not_applied_candidates=not_applied_keys,
        )

    @classmethod
    def _require_all(
        cls,
        flags: dict[str, bool],
        *,
        code: str,
        message: str,
    ) -> None:
        cls._require_flags(
            flags,
            tuple(flags),
            code=code,
            message=message,
        )

    @staticmethod
    def _require_flags(
        flags: dict[str, bool],
        required: tuple[str, ...],
        *,
        code: str,
        message: str,
    ) -> None:
        missing = tuple(
            key for key in required if not bool(flags.get(key))
        )
        if missing:
            raise PortalValidationError(
                message,
                code=code,
                metadata={"missing_flags": missing},
            )

    @staticmethod
    def _identity(value: object) -> str:
        return "".join(
            character
            for character in str(value).casefold()
            if character.isalnum()
        )

    @staticmethod
    def _confirmed(
        step: ContractStep,
        message: str,
        **metadata: object,
    ) -> PortalStepVerification:
        return PortalStepVerification(
            step=step,
            status=PortalVerificationStatus.CONFIRMED,
            message=message,
            metadata=metadata,
        )

    @staticmethod
    def _not_applied(
        step: ContractStep,
        message: str,
        **metadata: object,
    ) -> PortalStepVerification:
        return PortalStepVerification(
            step=step,
            status=PortalVerificationStatus.NOT_APPLIED,
            message=message,
            metadata=metadata,
        )

    @staticmethod
    def _ambiguous(
        step: ContractStep,
        message: str,
        **metadata: object,
    ) -> PortalStepVerification:
        return PortalStepVerification(
            step=step,
            status=PortalVerificationStatus.AMBIGUOUS,
            message=message,
            metadata=metadata,
        )
