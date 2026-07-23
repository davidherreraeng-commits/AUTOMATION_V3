from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


GENERAL_DATA_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="general.object_description",
        by=By.CSS_SELECTOR,
        value="textarea[name='objectDesc']",
        priority=10,
        description="Objeto del contrato mediante name=objectDesc.",
    ),
    LocatorSpec(
        key="general.object_description",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Objeto del Contrato'"
            ")]/following::textarea[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Objeto del Contrato.",
    ),
    LocatorSpec(
        key="general.signing_date",
        by=By.CSS_SELECTOR,
        value="input#signingDate",
        priority=10,
        description="Fecha de suscripción mediante id estable.",
    ),
    LocatorSpec(
        key="general.signing_date",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Fecha Suscripción'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Fecha Suscripción.",
    ),
    LocatorSpec(
        key="general.starting_date",
        by=By.CSS_SELECTOR,
        value="input#startingDate",
        priority=10,
        description="Fecha de inicio mediante id estable.",
    ),
    LocatorSpec(
        key="general.starting_date",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Fecha Inicio'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Fecha Inicio.",
    ),
    LocatorSpec(
        key="general.amount",
        by=By.CSS_SELECTOR,
        value="input[name='amount']",
        priority=10,
        description="Valor contractual en pesos.",
    ),
    LocatorSpec(
        key="general.amount",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Valor (COP)'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Valor (COP).",
    ),
    LocatorSpec(
        key="general.amount_in_words",
        by=By.CSS_SELECTOR,
        value="input[name='amountLetter']",
        priority=10,
        description="Valor contractual convertido a letras.",
    ),
    LocatorSpec(
        key="general.amount_in_words",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Valor en Letras'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Valor en Letras.",
    ),
    LocatorSpec(
        key="general.contract_term",
        by=By.CSS_SELECTOR,
        value="input[name='contractTermDays']",
        priority=10,
        description="Cantidad del plazo estimado.",
    ),
    LocatorSpec(
        key="general.contract_term",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Plazo Estimado'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Plazo Estimado.",
    ),
    LocatorSpec(
        key="general.term_unit_days",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='contractTimeUnit']"
            "[value='1']"
        ),
        priority=10,
        description="Unidad del plazo expresada en días.",
    ),
    LocatorSpec(
        key="general.term_unit_months",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='contractTimeUnit']"
            "[value='2']"
        ),
        priority=10,
        description="Unidad del plazo expresada en meses.",
    ),
    LocatorSpec(
        key="general.term_unit_years",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='contractTimeUnit']"
            "[value='3']"
        ),
        priority=10,
        description="Unidad del plazo expresada en años.",
    ),
    LocatorSpec(
        key="general.process_type",
        by=By.CSS_SELECTOR,
        value="input#processType",
        priority=10,
        description="Modalidad o proceso contractual.",
    ),
    LocatorSpec(
        key="general.process_type",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Modalidad o Proceso'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Modalidad o Proceso.",
    ),
    LocatorSpec(
        key="general.typology",
        by=By.CSS_SELECTOR,
        value="input#typology",
        priority=10,
        description="Procedimiento o causal contractual.",
    ),
    LocatorSpec(
        key="general.typology",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Procedimiento / Causal'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante Procedimiento o Causal.",
    ),
    LocatorSpec(
        key="general.contract_type",
        by=By.CSS_SELECTOR,
        value="input#type",
        priority=10,
        description="Tipo de contrato.",
    ),
    LocatorSpec(
        key="general.contract_type",
        by=By.XPATH,
        value=(
            "//label[contains("
            "normalize-space(.),"
            "'Tipo de Contrato'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Fallback mediante la etiqueta Tipo de Contrato.",
    ),
    LocatorSpec(
        key="general.other_currency_no",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='otherCurrencyFlag']"
            "[value='NO']"
        ),
        priority=10,
        description="Contrato no pactado en moneda extranjera.",
    ),
    LocatorSpec(
        key="general.other_currency_yes",
        by=By.CSS_SELECTOR,
        value=(
            "input[name='otherCurrencyFlag']"
            "[value='SI']"
        ),
        priority=10,
        description="Contrato pactado en moneda extranjera.",
    ),
)