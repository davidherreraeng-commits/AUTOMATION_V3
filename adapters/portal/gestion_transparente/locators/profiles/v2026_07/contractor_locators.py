from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


CONTRACTOR_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="contractor.dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//*[normalize-space()='Contratistas']]"
        ),
        priority=10,
        description="Diálogo específico de contratistas.",
    ),
    LocatorSpec(
        key="contractor.dialog",
        by=By.CSS_SELECTOR,
        value="[role='dialog'][aria-modal='true']",
        priority=20,
        description="Fallback para el diálogo modal.",
    ),
    LocatorSpec(
        key="contractor.nature.legal",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='contractorNature']"
            "[value='JURIDICA']"
        ),
        priority=10,
        description="Radio Persona Jurídica.",
    ),
    LocatorSpec(
        key="contractor.nature.natural",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='contractorNature']"
            "[value='NATURAL']"
        ),
        priority=10,
        description="Radio Persona Natural.",
    ),
    LocatorSpec(
        key="contractor.legal.id_type",
        by=By.CSS_SELECTOR,
        value="[role='dialog'] input#corpIdType",
        priority=10,
        description=(
            "Tipo de identificación de persona jurídica."
        ),
    ),
    LocatorSpec(
        key="contractor.legal.document_input",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "input[name='corpIdNumber']"
        ),
        priority=10,
        description=(
            "Identificación o NIT de persona jurídica."
        ),
    ),
    LocatorSpec(
        key="contractor.natural.id_type",
        by=By.CSS_SELECTOR,
        value="[role='dialog'] input#idType",
        priority=10,
        description=(
            "Tipo de identificación de persona natural."
        ),
    ),
    LocatorSpec(
        key="contractor.natural.document_input",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] input[name='idNumber']"
        ),
        priority=10,
        description=(
            "Identificación de persona natural."
        ),
    ),
    # Alias genérico conservado para componentes existentes.
    LocatorSpec(
        key="contractor.document_input",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "input[name='corpIdNumber']"
        ),
        priority=10,
        description="Documento jurídico.",
    ),
    LocatorSpec(
        key="contractor.document_input",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] input[name='idNumber']"
        ),
        priority=20,
        description="Documento natural.",
    ),
    LocatorSpec(
        key="contractor.search_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "//button[normalize-space()='Buscar']"
        ),
        priority=10,
        description="Busca contratistas.",
    ),
    LocatorSpec(
        key="contractor.result_row",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] [role='row'][data-id]"
        ),
        priority=10,
        description="Fila real del DataGrid.",
    ),
    LocatorSpec(
        key="contractor.result_row",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] .MuiDataGrid-row[data-id]"
        ),
        priority=20,
        description="Fallback de fila Material UI.",
    ),
    LocatorSpec(
        key="contractor.confirm_button",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "[role='row'][data-id] "
            "button[title='Seleccionar']"
        ),
        priority=10,
        description="Selecciona el contratista encontrado.",
    ),
    LocatorSpec(
        key="contractor.confirm_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "//*[@role='row' and @data-id]"
            "//button[@title='Seleccionar']"
        ),
        priority=20,
        description="Fallback XPath de selección.",
    ),
)