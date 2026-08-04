from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


ADDITIONAL_DATES_HEADING = (
    "VINCULAR FECHAS / NUEVO CONTRATO"
)

FILE_REPORTED_HEADING = (
    "VINCULAR ANEXOS / NUEVO CONTRATO"
)


ADDITIONAL_DATES_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="additional_dates.section",
        by=By.XPATH,
        value=(
            f"//p[normalize-space()="
            f"'{ADDITIONAL_DATES_HEADING}']"
        ),
        priority=10,
        description=(
            "Encabezado de la etapa de fechas adicionales."
        ),
    ),
    LocatorSpec(
        key="additional_dates.section",
        by=By.CSS_SELECTOR,
        value="input[name='additionalDates.0.value']",
        priority=20,
        description=(
            "Fallback mediante el primer campo de fechas "
            "adicionales."
        ),
    ),
    LocatorSpec(
        key="additional_dates.opening_date_input",
        by=By.CSS_SELECTOR,
        value="input[name='additionalDates.0.value']",
        priority=10,
        description=(
            "Fecha de apertura o invitación."
        ),
    ),
    LocatorSpec(
        key="additional_dates.guarantee_approval_date_input",
        by=By.CSS_SELECTOR,
        value="input[name='additionalDates.1.value']",
        priority=10,
        description=(
            "Fecha de aprobación de la garantía única."
        ),
    ),
    LocatorSpec(
        key="additional_dates.web_publication_date_input",
        by=By.CSS_SELECTOR,
        value="input[name='additionalDates.2.value']",
        priority=10,
        description=(
            "Fecha de publicación en la página web."
        ),
    ),
    LocatorSpec(
        key="additional_dates.secop_publication_date_input",
        by=By.CSS_SELECTOR,
        value="input[name='additionalDates.3.value']",
        priority=10,
        description=(
            "Fecha de publicación en SECOP."
        ),
    ),
    LocatorSpec(
        key="additional_dates.calendar_dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog' "
            "and @aria-label='Choose Date']"
        ),
        priority=10,
        description=(
            "Calendario react-datepicker abierto para "
            "seleccionar una fecha."
        ),
    ),
    LocatorSpec(
        key="additional_dates.calendar_day_option",
        by=By.XPATH,
        value=(
            "//*[@role='dialog' "
            "and @aria-label='Choose Date']"
            "//*[@role='option' and @aria-label]"
        ),
        priority=10,
        description=(
            "Día disponible dentro del calendario."
        ),
    ),
    LocatorSpec(
        key="additional_dates.validate_button",
        by=By.XPATH,
        value=(
            "//input[@name='additionalDates.0.value']"
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
            "Botón Validar contenido en la tarjeta "
            "de fechas adicionales."
        ),
    ),
    LocatorSpec(
        key="additional_dates.validate_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{ADDITIONAL_DATES_HEADING}']"
            "/following::button["
            "normalize-space()='Validar'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de Validar desde el encabezado "
            "de fechas adicionales."
        ),
    ),
    LocatorSpec(
        key="additional_dates.skip_button",
        by=By.XPATH,
        value=(
            "//input[@name='additionalDates.0.value']"
            "/ancestor::div["
            "contains("
            "concat(' ', normalize-space(@class), ' '),"
            "' MuiCard-root '"
            ")"
            "][1]"
            "//button[normalize-space()='Saltar Paso']"
        ),
        priority=10,
        description=(
            "Botón para omitir las fechas adicionales "
            "cuando ninguna sea aplicable."
        ),
    ),
    LocatorSpec(
        key="additional_dates.skip_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{ADDITIONAL_DATES_HEADING}']"
            "/following::button["
            "normalize-space()='Saltar Paso'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de Saltar Paso desde el encabezado."
        ),
    ),
    LocatorSpec(
        key="additional_dates.validation_success",
        by=By.XPATH,
        value=(
            "//input[@name='additionalDates.0.value']"
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
            "Las fechas fueron validadas cuando aparece "
            "Vincular en la misma tarjeta."
        ),
    ),
    LocatorSpec(
        key="additional_dates.validation_success",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{ADDITIONAL_DATES_HEADING}']"
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
        key="additional_dates.link_button",
        by=By.XPATH,
        value=(
            "//input[@name='additionalDates.0.value']"
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
            "Botón Vincular de las fechas adicionales."
        ),
    ),
    LocatorSpec(
        key="additional_dates.link_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            f"'{ADDITIONAL_DATES_HEADING}']"
            "/following::button["
            "normalize-space()='Vincular'"
            "][1]"
        ),
        priority=20,
        description=(
            "Fallback de Vincular desde el encabezado."
        ),
    ),
    LocatorSpec(
        key="additional_dates.link_success_dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "[.//*[contains("
            "normalize-space(.),"
            "'Se han vinculado las fechas adicionales "
            "al contrato exitosamente'"
            ")]]"
        ),
        priority=10,
        description=(
            "Diálogo que confirma la vinculación exitosa "
            "de las fechas adicionales."
        ),
    ),
    LocatorSpec(
        key="additional_dates.link_success_accept",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "//button[normalize-space()='Aceptar']"
        ),
        priority=10,
        description=(
            "Botón Aceptar del diálogo de vinculación "
            "de fechas adicionales."
        ),
    ),
    LocatorSpec(
        key="additional_dates.linked",
        by=By.XPATH,
        value=(
            f"//p[normalize-space()="
            f"'{FILE_REPORTED_HEADING}']"
        ),
        priority=10,
        description=(
            "Las fechas quedaron vinculadas cuando "
            "aparece la etapa de anexos."
        ),
    ),
    LocatorSpec(
        key="additional_dates.linked",
        by=By.CSS_SELECTOR,
        value="input[type='file']",
        priority=20,
        description=(
            "Fallback mediante el control de carga "
            "de anexos."
        ),
    ),
    LocatorSpec(
        key="file_reported.section",
        by=By.XPATH,
        value=(
            f"//p[normalize-space()="
            f"'{FILE_REPORTED_HEADING}']"
        ),
        priority=10,
        description=(
            "Encabezado de la etapa de anexos "
            "del contrato."
        ),
    ),
    LocatorSpec(
        key="file_reported.section",
        by=By.CSS_SELECTOR,
        value="input[type='file']",
        priority=20,
        description=(
            "Fallback mediante el control de archivo."
        ),
    ),
)