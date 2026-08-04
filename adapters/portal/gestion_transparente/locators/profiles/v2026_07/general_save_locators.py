from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


GENERAL_SAVE_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="general.final_validate_button",
        by=By.XPATH,
        value=(
            "//form[.//input[@id='executionCity']]"
            "//button[normalize-space()='Validar']"
        ),
        priority=10,
        description=(
            "Segundo botón Validar, contextualizado dentro "
            "del formulario final de datos generales."
        ),
    ),
    LocatorSpec(
        key="general.validation_success",
        by=By.XPATH,
        value=(
            "//form[.//input[@id='executionCity']]"
            "//button[normalize-space()='Guardar']"
        ),
        priority=10,
        description=(
            "Los datos generales quedaron validados cuando "
            "el botón Guardar reemplaza al botón Validar."
        ),
    ),
    LocatorSpec(
        key="general.save_button",
        by=By.XPATH,
        value=(
            "//form[.//input[@id='executionCity']]"
            "//button[normalize-space()='Guardar']"
        ),
        priority=10,
        description=(
            "Botón Guardar del formulario general validado."
        ),
    ),
    LocatorSpec(
        key="general.save_success_dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "[.//*[contains("
            "normalize-space(.),"
            "'Se ha registrado el contrato exitosamente'"
            ")]]"
        ),
        priority=10,
        description=(
            "Diálogo que confirma el registro exitoso "
            "del contrato."
        ),
    ),
    LocatorSpec(
        key="general.save_success_accept",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "//button[normalize-space()='Aceptar']"
        ),
        priority=10,
        description=(
            "Botón Aceptar del diálogo de registro exitoso."
        ),
    ),
    LocatorSpec(
        key="general.contract_saved",
        by=By.CSS_SELECTOR,
        value="input[name='CONTRACT_IDENTIFIER']",
        priority=10,
        description=(
            "Número contractual cargado en la siguiente "
            "etapa después de guardar."
        ),
    ),
    LocatorSpec(
        key="general.contract_saved",
        by=By.CSS_SELECTOR,
        value="input[name='CONTRACTOR_IDENTIFIER']",
        priority=20,
        description=(
            "Fallback mediante la identificación del "
            "contratista cargada en la siguiente etapa."
        ),
    ),
    LocatorSpec(
        key="supervisor.section",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            "'VINCULAR INTERVENTOR/SUPERVISOR / "
            "NUEVO CONTRATO']"
        ),
        priority=10,
        description=(
            "Encabezado de la etapa de interventor "
            "o supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.section",
        by=By.CSS_SELECTOR,
        value=(
            "button[title="
            "'Buscar Interventor / Supervisor']"
        ),
        priority=20,
        description=(
            "Fallback mediante el botón de búsqueda "
            "de interventor o supervisor."
        ),
    ),
)