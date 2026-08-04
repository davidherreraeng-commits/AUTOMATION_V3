from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


GENERAL_COMPLETION_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="general.government_plan",
        by=By.CSS_SELECTOR,
        value="input#budgetDevPlan",
        priority=10,
        description="Plan de Gobierno.",
    ),
    LocatorSpec(
        key="general.government_plan",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Plan de Gobierno'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Plan de Gobierno.",
    ),
    LocatorSpec(
        key="general.budget_year",
        by=By.CSS_SELECTOR,
        value="input#budgetYear",
        priority=10,
        description="Año al que aplica el rubro presupuestal.",
    ),
    LocatorSpec(
        key="general.budget_year",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Año al que aplica el Rubro'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta del año del rubro.",
    ),
    LocatorSpec(
        key="general.budget_item",
        by=By.CSS_SELECTOR,
        value="input#budgetItem",
        priority=10,
        description="Rubro presupuestal del contrato.",
    ),
    LocatorSpec(
        key="general.budget_item",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Rubro Presupuestal'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Rubro Presupuestal.",
    ),
    LocatorSpec(
        key="general.budget_subsector",
        by=By.CSS_SELECTOR,
        value="input#budgetExpenditureSubSector",
        priority=10,
        description="Subsector presupuestal.",
    ),
    LocatorSpec(
        key="general.budget_subsector",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Sub-Sector'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Sub-Sector.",
    ),
    LocatorSpec(
        key="general.budget_link_button",
        by=By.XPATH,
        value=(
            "//input[@id='budgetExpenditureSubSector']"
            "/following::button[normalize-space()='Vincular'][1]"
        ),
        priority=10,
        description=(
            "Botón Vincular correspondiente a la clasificación "
            "presupuestal de los datos generales."
        ),
    ),
    LocatorSpec(
        key="general.secop_yes",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='secopPublication']"
            "[value='SI']"
        ),
        priority=10,
        description="Indica que el contrato fue publicado en SECOP.",
    ),
    LocatorSpec(
        key="general.secop_no",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='secopPublication']"
            "[value='NO']"
        ),
        priority=10,
        description="Indica que el contrato no fue publicado en SECOP.",
    ),
    LocatorSpec(
        key="general.secop_url",
        by=By.CSS_SELECTOR,
        value="input[name='secopURL']",
        priority=10,
        description="URL del contrato en SECOP.",
    ),
    LocatorSpec(
        key="general.secop_url",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'URL del Contrato en el SECOP'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta de URL SECOP.",
    ),
    LocatorSpec(
        key="general.advance_no",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='advanceDefined']"
            "[value='NO']"
        ),
        priority=10,
        description="Contrato sin anticipo.",
    ),
    LocatorSpec(
        key="general.commercial_trust_no",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='commercialTrust']"
            "[value='NO']"
        ),
        priority=10,
        description="Contrato sin fiducia mercantil.",
    ),
    LocatorSpec(
        key="general.urgency_no",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='urgencyManifest']"
            "[value='NO']"
        ),
        priority=10,
        description="Contrato sin urgencia manifiesta.",
    ),
    LocatorSpec(
        key="general.future_commitment_no",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='validityFuture']"
            "[value='NO']"
        ),
        priority=10,
        description="Contrato sin vigencia futura.",
    ),
    LocatorSpec(
        key="general.cooperation_contract_no",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='cooperationContract']"
            "[value='NO']"
        ),
        priority=10,
        description="El registro no corresponde a un convenio.",
    ),
    LocatorSpec(
        key="general.execution_department",
        by=By.CSS_SELECTOR,
        value="input#executionProvince",
        priority=10,
        description="Departamento de ejecución.",
    ),
    LocatorSpec(
        key="general.execution_department",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Departamento de Ejecución'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante Departamento de Ejecución.",
    ),
    LocatorSpec(
        key="general.execution_city",
        by=By.CSS_SELECTOR,
        value="input#executionCity",
        priority=10,
        description="Municipio de ejecución.",
    ),
    LocatorSpec(
        key="general.execution_city",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Municipio de Ejecución'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante Municipio de Ejecución.",
    ),
)