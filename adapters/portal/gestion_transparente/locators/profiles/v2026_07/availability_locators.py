from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


AVAILABLE_SECTION_HEADING = (
    "Seleccione la Disponibilidad a vincular al Contrato"
)

LINKED_SECTION_HEADING = (
    "Disponibilidades Vinculadas al Contrato"
)

BUDGET_REGISTER_HEADING = (
    "RETIRAR REGISTRO PRESUPUESTAL / EDITAR CONTRATO"
)


AVAILABILITY_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="availability.search_input",
        by=By.XPATH,
        value=(
            f"//h6[normalize-space()="
            f"'{AVAILABLE_SECTION_HEADING}']"
            "/following::input[@id='search'][1]"
        ),
        priority=10,
        description=(
            "Campo Buscar correspondiente a la tabla de "
            "disponibilidades disponibles."
        ),
    ),
    LocatorSpec(
        key="availability.available_row",
        by=By.XPATH,
        value=(
            f"//h6[normalize-space()="
            f"'{AVAILABLE_SECTION_HEADING}']"
            "/following::*[@role='grid'][1]"
            "//*[@role='row' and @data-id]"
        ),
        priority=10,
        description=(
            "Fila real de la tabla de disponibilidades "
            "disponibles."
        ),
    ),
    LocatorSpec(
        key="availability.cdp_cell",
        by=By.XPATH,
        value=(
            f"//h6[normalize-space()="
            f"'{AVAILABLE_SECTION_HEADING}']"
            "/following::*[@role='grid'][1]"
            "//*[@role='gridcell' and "
            "@data-field='BUDGET_AVAILABILITY_IDENTIFIER']"
        ),
        priority=10,
        description=(
            "Celda que contiene el código CDP de una "
            "disponibilidad disponible."
        ),
    ),
    LocatorSpec(
        key="availability.link_button",
        by=By.XPATH,
        value=(
            f"//h6[normalize-space()="
            f"'{AVAILABLE_SECTION_HEADING}']"
            "/following::*[@role='grid'][1]"
            "//*[@role='row' and @data-id]"
            "//button[@title='Vincular']"
        ),
        priority=10,
        description=(
            "Botón Vincular perteneciente a una fila "
            "de disponibilidad."
        ),
    ),
    LocatorSpec(
        key="availability.link_success",
        by=By.XPATH,
        value=(
            "//*[@role='status' and contains("
            "normalize-space(.),"
            "'Se ha vinculado la disponibilidad "
            "presupuestal exitosamente'"
            ")]"
        ),
        priority=10,
        description=(
            "Notificación temporal de vinculación "
            "presupuestal exitosa."
        ),
    ),
    LocatorSpec(
        key="availability.linked_section",
        by=By.XPATH,
        value=(
            f"//h6[normalize-space()="
            f"'{LINKED_SECTION_HEADING}']"
        ),
        priority=10,
        description=(
            "Encabezado de disponibilidades vinculadas "
            "al contrato."
        ),
    ),
    LocatorSpec(
        key="availability.linked_row",
        by=By.XPATH,
        value=(
            f"//h6[normalize-space()="
            f"'{LINKED_SECTION_HEADING}']"
            "/following::*[@role='grid'][1]"
            "//*[@role='row' and @data-id]"
        ),
        priority=10,
        description=(
            "Fila persistente de una disponibilidad "
            "ya vinculada al contrato."
        ),
    ),
    LocatorSpec(
        key="availability.continue_button",
        by=By.XPATH,
        value="//button[normalize-space()='Continuar']",
        priority=10,
        description=(
            "Botón que avanza desde disponibilidad "
            "hacia registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="availability.linked",
        by=By.XPATH,
        value=(
            f"//p[normalize-space()="
            f"'{BUDGET_REGISTER_HEADING}']"
        ),
        priority=10,
        description=(
            "La disponibilidad quedó vinculada cuando "
            "el flujo avanza al registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="availability.linked",
        by=By.CSS_SELECTOR,
        value="input[name='budgetRegister.0.register']",
        priority=20,
        description=(
            "Fallback mediante el campo de número de "
            "registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.section",
        by=By.XPATH,
        value=(
            f"//p[normalize-space()="
            f"'{BUDGET_REGISTER_HEADING}']"
        ),
        priority=10,
        description=(
            "Encabezado de la etapa de registro "
            "presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.section",
        by=By.CSS_SELECTOR,
        value="input[name='budgetRegister.0.register']",
        priority=20,
        description=(
            "Fallback mediante el primer campo del "
            "registro presupuestal."
        ),
    ),
)