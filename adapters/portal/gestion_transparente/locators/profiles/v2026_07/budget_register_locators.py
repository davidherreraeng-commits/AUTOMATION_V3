<<<<<<< HEAD
from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


BUDGET_REGISTER_HEADING = (
    "RETIRAR REGISTRO PRESUPUESTAL / EDITAR CONTRATO"
)

ADDITIONAL_DATES_HEADING = (
    "VINCULAR FECHAS / NUEVO CONTRATO"
)


BUDGET_REGISTER_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="budget_register.number_input",
        by=By.CSS_SELECTOR,
        value="input[name='budgetRegister.0.register']",
        priority=10,
        description=(
            "Número del registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.date_input",
        by=By.XPATH,
        value=(
            "//label[normalize-space()="
            "'Fecha Registro Presupuestal']"
            "/following::input[1]"
        ),
        priority=10,
        description=(
            "Fecha del registro presupuestal localizada "
            "mediante su etiqueta estable."
        ),
    ),
    LocatorSpec(
        key="budget_register.availability_select",
        by=By.XPATH,
        value=(
            "//input["
            "@name="
            "'budgetRegister[0].availability[0].value'"
            "]"
            "/preceding-sibling::*"
            "[@role='combobox'][1]"
        ),
        priority=10,
        description=(
            "Selector visible de la disponibilidad "
            "presupuestal vinculada."
        ),
    ),
    LocatorSpec(
        key="budget_register.availability_option",
        by=By.XPATH,
        value=(
            "//*[@role='listbox']"
            "//*[@role='option' and @data-value]"
        ),
        priority=10,
        description=(
            "Opción real del selector de disponibilidad "
            "presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.gross_total_input",
        by=By.CSS_SELECTOR,
        value=(
            "input[name="
            "'budgetRegister[0].availability[0].amount'"
            "]"
        ),
        priority=10,
        description=(
            "Valor total bruto asociado al registro "
            "presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.validate_button",
        by=By.XPATH,
        value=(
            "//input[@name='budgetRegister.0.register']"
            "/ancestor::div["
            "contains("
            "concat(' ', normalize-space(@class), ' '),"
            "' MuiCard-root '"
            ")"
            "][1]"
            "//button[normalize-space()='Validar']"
        ),
        priority=10,
        description=(
            "Botón Validar contenido en la tarjeta del "
            "registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.validate_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{BUDGET_REGISTER_HEADING}']"
            "/following::button["
            "normalize-space()='Validar'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de Validar desde el encabezado "
            "de registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.validation_success",
        by=By.XPATH,
        value=(
            "//input[@name='budgetRegister.0.register']"
            "/ancestor::div["
            "contains("
            "concat(' ', normalize-space(@class), ' '),"
            "' MuiCard-root '"
            ")"
            "][1]"
            "//button[normalize-space()='Vincular']"
        ),
        priority=10,
        description=(
            "La validación fue exitosa cuando aparece "
            "Vincular dentro de la misma tarjeta."
        ),
    ),
    LocatorSpec(
        key="budget_register.validation_success",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{BUDGET_REGISTER_HEADING}']"
            "/following::button["
            "normalize-space()='Vincular'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de la postcondición de validación."
        ),
    ),
    LocatorSpec(
        key="budget_register.link_button",
        by=By.XPATH,
        value=(
            "//input[@name='budgetRegister.0.register']"
            "/ancestor::div["
            "contains("
            "concat(' ', normalize-space(@class), ' '),"
            "' MuiCard-root '"
            ")"
            "][1]"
            "//button[normalize-space()='Vincular']"
        ),
        priority=10,
        description=(
            "Botón Vincular del registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.link_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{BUDGET_REGISTER_HEADING}']"
            "/following::button["
            "normalize-space()='Vincular'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de Vincular desde el encabezado "
            "de la etapa."
        ),
    ),
    LocatorSpec(
        key="budget_register.link_success_dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "[.//*[contains("
            "normalize-space(.),"
            "'Se ha vinculado el registro presupuestal "
            "al contrato exitosamente'"
            ")]]"
        ),
        priority=10,
        description=(
            "Diálogo que confirma la vinculación exitosa "
            "del registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.link_success_accept",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "//button[normalize-space()='Aceptar']"
        ),
        priority=10,
        description=(
            "Botón Aceptar del diálogo de vinculación "
            "del registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.linked",
        by=By.XPATH,
        value=(
            f"//p[normalize-space()="
            f"'{ADDITIONAL_DATES_HEADING}']"
        ),
        priority=10,
        description=(
            "El registro quedó vinculado cuando aparece "
            "la etapa de fechas adicionales."
        ),
    ),
    LocatorSpec(
        key="budget_register.linked",
        by=By.CSS_SELECTOR,
        value="input[name='additionalDates.0.value']",
        priority=20,
        description=(
            "Fallback mediante el primer campo de fechas "
            "adicionales."
        ),
    ),
=======
from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


BUDGET_REGISTER_HEADING = (
    "RETIRAR REGISTRO PRESUPUESTAL / EDITAR CONTRATO"
)

ADDITIONAL_DATES_HEADING = (
    "VINCULAR FECHAS / NUEVO CONTRATO"
)


BUDGET_REGISTER_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="budget_register.number_input",
        by=By.CSS_SELECTOR,
        value="input[name='budgetRegister.0.register']",
        priority=10,
        description=(
            "Número del registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.date_input",
        by=By.XPATH,
        value=(
            "//label[normalize-space()="
            "'Fecha Registro Presupuestal']"
            "/following::input[1]"
        ),
        priority=10,
        description=(
            "Fecha del registro presupuestal localizada "
            "mediante su etiqueta estable."
        ),
    ),
    LocatorSpec(
        key="budget_register.availability_select",
        by=By.XPATH,
        value=(
            "//input["
            "@name="
            "'budgetRegister[0].availability[0].value'"
            "]"
            "/preceding-sibling::*"
            "[@role='combobox'][1]"
        ),
        priority=10,
        description=(
            "Selector visible de la disponibilidad "
            "presupuestal vinculada."
        ),
    ),
    LocatorSpec(
        key="budget_register.availability_option",
        by=By.XPATH,
        value=(
            "//*[@role='listbox']"
            "//*[@role='option' and @data-value]"
        ),
        priority=10,
        description=(
            "Opción real del selector de disponibilidad "
            "presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.gross_total_input",
        by=By.CSS_SELECTOR,
        value=(
            "input[name="
            "'budgetRegister[0].availability[0].amount'"
            "]"
        ),
        priority=10,
        description=(
            "Valor total bruto asociado al registro "
            "presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.validate_button",
        by=By.XPATH,
        value=(
            "//input[@name='budgetRegister.0.register']"
            "/ancestor::div["
            "contains("
            "concat(' ', normalize-space(@class), ' '),"
            "' MuiCard-root '"
            ")"
            "][1]"
            "//button[normalize-space()='Validar']"
        ),
        priority=10,
        description=(
            "Botón Validar contenido en la tarjeta del "
            "registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.validate_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{BUDGET_REGISTER_HEADING}']"
            "/following::button["
            "normalize-space()='Validar'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de Validar desde el encabezado "
            "de registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.validation_success",
        by=By.XPATH,
        value=(
            "//input[@name='budgetRegister.0.register']"
            "/ancestor::div["
            "contains("
            "concat(' ', normalize-space(@class), ' '),"
            "' MuiCard-root '"
            ")"
            "][1]"
            "//button[normalize-space()='Vincular']"
        ),
        priority=10,
        description=(
            "La validación fue exitosa cuando aparece "
            "Vincular dentro de la misma tarjeta."
        ),
    ),
    LocatorSpec(
        key="budget_register.validation_success",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{BUDGET_REGISTER_HEADING}']"
            "/following::button["
            "normalize-space()='Vincular'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de la postcondición de validación."
        ),
    ),
    LocatorSpec(
        key="budget_register.link_button",
        by=By.XPATH,
        value=(
            "//input[@name='budgetRegister.0.register']"
            "/ancestor::div["
            "contains("
            "concat(' ', normalize-space(@class), ' '),"
            "' MuiCard-root '"
            ")"
            "][1]"
            "//button[normalize-space()='Vincular']"
        ),
        priority=10,
        description=(
            "Botón Vincular del registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.link_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{BUDGET_REGISTER_HEADING}']"
            "/following::button["
            "normalize-space()='Vincular'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de Vincular desde el encabezado "
            "de la etapa."
        ),
    ),
    LocatorSpec(
        key="budget_register.link_success_dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "[.//*[contains("
            "normalize-space(.),"
            "'Se ha vinculado el registro presupuestal "
            "al contrato exitosamente'"
            ")]]"
        ),
        priority=10,
        description=(
            "Diálogo que confirma la vinculación exitosa "
            "del registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.link_success_accept",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "//button[normalize-space()='Aceptar']"
        ),
        priority=10,
        description=(
            "Botón Aceptar del diálogo de vinculación "
            "del registro presupuestal."
        ),
    ),
    LocatorSpec(
        key="budget_register.linked",
        by=By.XPATH,
        value=(
            f"//p[normalize-space()="
            f"'{ADDITIONAL_DATES_HEADING}']"
        ),
        priority=10,
        description=(
            "El registro quedó vinculado cuando aparece "
            "la etapa de fechas adicionales."
        ),
    ),
    LocatorSpec(
        key="budget_register.linked",
        by=By.CSS_SELECTOR,
        value="input[name='additionalDates.0.value']",
        priority=20,
        description=(
            "Fallback mediante el primer campo de fechas "
            "adicionales."
        ),
    ),
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
)