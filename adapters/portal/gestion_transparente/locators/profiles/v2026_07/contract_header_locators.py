from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


CONTRACT_HEADER_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="contract.header.record_type_contract",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='contractType'][value='1']"
        ),
        priority=10,
        description=(
            "Radio Contrato del tipo de registro."
        ),
    ),
    LocatorSpec(
        key="contract.header.record_type_contract",
        by=By.XPATH,
        value=(
            "//span[normalize-space()='Contrato']"
            "/preceding::input"
            "[@name='contractType' and @value='1'][1]"
        ),
        priority=20,
        description=(
            "Fallback mediante la etiqueta Contrato."
        ),
    ),
    LocatorSpec(
        key="contract.header.contract_number",
        by=By.CSS_SELECTOR,
        value="input[name='code']",
        priority=10,
        description="Número contractual mediante name=code.",
    ),
    LocatorSpec(
        key="contract.header.contract_number",
        by=By.XPATH,
        value=(
            "//label[starts-with(normalize-space(.),'Número')]"
            "/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Número.",
    ),
    LocatorSpec(
        key="contract.header.contractor_link",
        by=By.CSS_SELECTOR,
        value=(
            "button[aria-label='buscar contratista']"
        ),
        priority=10,
        description="Abre la búsqueda de contratistas.",
    ),
    LocatorSpec(
        key="contract.header.contractor_link",
        by=By.CSS_SELECTOR,
        value="button[title='Buscar Contratista']",
        priority=20,
        description="Fallback mediante title.",
    ),
    LocatorSpec(
        key="contract.header.project_link",
        by=By.CSS_SELECTOR,
        value="button[aria-label='buscar proyecto']",
        priority=10,
        description="Abre la búsqueda de proyectos.",
    ),
    LocatorSpec(
        key="contract.header.project_link",
        by=By.CSS_SELECTOR,
        value="button[title='Buscar Proyecto']",
        priority=20,
        description="Fallback mediante title.",
    ),
    LocatorSpec(
        key="contract.header.validate_button",
        by=By.XPATH,
        value="//button[normalize-space()='Validar']",
        priority=10,
        description="Primera validación de la cabecera.",
    ),
    LocatorSpec(
    key="contract.header.validation_success",
    by=By.CSS_SELECTOR,
    value="textarea[name='objectDesc']",
    priority=10,
    description=(
        "La primera validación fue exitosa cuando aparece "
        "el campo Objeto del Contrato."
    ),
),
LocatorSpec(
    key="contract.header.validation_success",
    by=By.CSS_SELECTOR,
    value="input#signingDate",
    priority=20,
    description=(
        "Fallback mediante el campo Fecha de Suscripción, "
        "visible después de validar la cabecera."
    ),
),
LocatorSpec(
    key="contract.header.validation_success",
    by=By.XPATH,
    value=(
        "//*["
        "@role='dialog' or @role='alert'"
        "][contains("
        "translate("
        "normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ',"
        "'abcdefghijklmnopqrstuvwxyzáéíóú'"
        "),"
        "'éxito'"
        ")]"
    ),
    priority=30,
    description=(
        "Fallback para una eventual confirmación explícita "
        "de éxito."
    ),
),
)