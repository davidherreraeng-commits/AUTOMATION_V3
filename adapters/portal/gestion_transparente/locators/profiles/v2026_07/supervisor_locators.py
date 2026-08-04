from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


SUPERVISOR_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="supervisor.search_open",
        by=By.CSS_SELECTOR,
        value=(
            "button[title="
            "'Buscar Interventor / Supervisor']"
        ),
        priority=10,
        description=(
            "Abre el diálogo de búsqueda del interventor "
            "o supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Interventores']]"
        ),
        priority=10,
        description=(
            "Diálogo específico de búsqueda de interventores."
        ),
    ),
    LocatorSpec(
        key="supervisor.dialog",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog']"
            "[aria-labelledby='customized-dialog-title']"
        ),
        priority=20,
        description=(
            "Fallback mediante los atributos del diálogo."
        ),
    ),
    LocatorSpec(
        key="supervisor.nature_person",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "input[name='controlerNature']"
            "[value='PERSON']"
        ),
        priority=10,
        description=(
            "Selecciona la naturaleza Persona."
        ),
    ),
    LocatorSpec(
        key="supervisor.id_type",
        by=By.CSS_SELECTOR,
        value="[role='dialog'] input#idType",
        priority=10,
        description=(
            "Tipo de identificación del supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.document_input",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "input[name='idNumber']"
        ),
        priority=10,
        description=(
            "Número de identificación del supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.search_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Interventores']]"
            "//button["
            "translate(normalize-space(.), 'buscar', 'BUSCAR')="
            "'BUSCAR'"
            "]"
        ),
        priority=10,
        description=(
            "Ejecuta la búsqueda explícita del supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.search_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "//button["
            ".//*[translate(normalize-space(.), "
            "'buscar', 'BUSCAR')='BUSCAR']"
            "]"
        ),
        priority=20,
        description=(
            "Fallback del botón Buscar mediante su texto descendiente."
        ),
    ),
    LocatorSpec(
        key="supervisor.result_row",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "[role='row'][data-id]"
        ),
        priority=10,
        description=(
            "Fila real de la lista de coincidencias."
        ),
    ),
    LocatorSpec(
        key="supervisor.result_row",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            ".MuiDataGrid-row[data-id]"
        ),
        priority=20,
        description=(
            "Fallback mediante la fila Material UI."
        ),
    ),
    LocatorSpec(
        key="supervisor.select_button",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "[role='row'][data-id] "
            "button[title='Seleccionar']"
        ),
        priority=10,
        description=(
            "Selecciona la coincidencia del supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.select_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "//*[@role='row' and @data-id]"
            "//button[@title='Seleccionar']"
        ),
        priority=20,
        description=(
            "Fallback XPath del botón Seleccionar."
        ),
    ),
    LocatorSpec(
        key="supervisor.selected_identifier",
        by=By.XPATH,
        value=(
            "//button["
            "@title='Buscar Interventor / Supervisor'"
            "]"
            "/ancestor::div["
            "contains(@class,'MuiInputBase-root')"
            "][1]"
            "//input"
        ),
        priority=10,
        description=(
            "Identificación del supervisor seleccionada "
            "en el formulario principal."
        ),
    ),
    LocatorSpec(
        key="supervisor.type_input",
        by=By.XPATH,
        value=(
            "//input[@name='controler.0.type']"
            "/preceding-sibling::*"
            "[@role='combobox'][1]"
        ),
        priority=10,
        description=(
            "Selector visible del tipo de supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.contract_input",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='controler.0.contractId']"
        ),
        priority=10,
        description=(
            "Contrato del interventor o supervisor."
        ),
    ),
        LocatorSpec(
        key="supervisor.validate_button",
        by=By.XPATH,
        value=(
            "//input[@name='controler.0.type']"
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
            "Botón Validar ubicado en la misma tarjeta "
            "Material UI del supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.validate_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            "'VINCULAR INTERVENTOR/SUPERVISOR / "
            "NUEVO CONTRATO']"
            "/following::button[normalize-space()='Validar'][1]"
        ),
        priority=20,
        description=(
            "Fallback de Validar desde el encabezado "
            "de la etapa de supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.validation_success",
        by=By.XPATH,
        value=(
            "//input[@name='controler.0.type']"
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
            "La validación del supervisor fue exitosa "
            "cuando aparece Vincular en la misma tarjeta."
        ),
    ),
    LocatorSpec(
        key="supervisor.validation_success",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            "'VINCULAR INTERVENTOR/SUPERVISOR / "
            "NUEVO CONTRATO']"
            "/following::button[normalize-space()='Vincular'][1]"
        ),
        priority=20,
        description=(
            "Fallback de la postcondición de validación "
            "desde el encabezado de la etapa."
        ),
    ),
    LocatorSpec(
        key="supervisor.link_button",
        by=By.XPATH,
        value=(
            "//input[@name='controler.0.type']"
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
            "Botón Vincular ubicado en la misma tarjeta "
            "Material UI del supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.link_button",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            "'VINCULAR INTERVENTOR/SUPERVISOR / "
            "NUEVO CONTRATO']"
            "/following::button[normalize-space()='Vincular'][1]"
        ),
        priority=20,
        description=(
            "Fallback de Vincular desde el encabezado "
            "de la etapa de supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.link_success_dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "[.//*[contains("
            "normalize-space(.),"
            "'Se ha vinculado el interventor exitosamente'"
            ")]]"
        ),
        priority=10,
        description=(
            "Diálogo que confirma la vinculación "
            "del supervisor."
        ),
    ),
    LocatorSpec(
        key="supervisor.link_success_accept",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//h2[normalize-space()='Éxito']]"
            "//button[normalize-space()='Aceptar']"
        ),
        priority=10,
        description=(
            "Botón Aceptar del diálogo de vinculación."
        ),
    ),
    LocatorSpec(
        key="supervisor.linked",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            "'VINCULAR DISPONIBILIDAD PRESUPUESTAL "
            "/ NUEVO CONTRATO']"
        ),
        priority=10,
        description=(
            "La vinculación terminó cuando aparece "
            "la etapa de disponibilidad."
        ),
    ),
    LocatorSpec(
        key="supervisor.linked",
        by=By.XPATH,
        value=(
            "//h6[normalize-space()="
            "'Seleccione la Disponibilidad a vincular "
            "al Contrato']"
        ),
        priority=20,
        description=(
            "Fallback mediante el encabezado de la tabla "
            "de disponibilidades."
        ),
    ),
    LocatorSpec(
        key="availability.section",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            "'VINCULAR DISPONIBILIDAD PRESUPUESTAL "
            "/ NUEVO CONTRATO']"
        ),
        priority=10,
        description=(
            "Encabezado principal de disponibilidad "
            "presupuestal."
        ),
    ),
    LocatorSpec(
        key="availability.section",
        by=By.XPATH,
        value=(
            "//h6[normalize-space()="
            "'Seleccione la Disponibilidad a vincular "
            "al Contrato']"
        ),
        priority=20,
        description=(
            "Fallback mediante la sección de selección "
            "de disponibilidad."
        ),
    ),
)