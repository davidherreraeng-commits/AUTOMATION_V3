from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


BUDGET_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
    key="budget.section",
    by=By.XPATH,
    value=(
        "//*["
        "not(ancestor::nav)"
        " and "
        "("
        "self::h1 or self::h2 or self::h3 "
        "or self::h4 or self::h5 or self::h6 "
        "or @role='heading'"
        ")"
        " and "
        "contains("
        "translate("
        "normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ',"
        "'abcdefghijklmnopqrstuvwxyzáéíóú'"
        "),"
        "'presupuest'"
        ")"
        "]"
    ),
    priority=10,
    description=(
        "Encabezado presupuestal fuera del menú lateral."
    ),
),
LocatorSpec(
    key="budget.section",
    by=By.XPATH,
    value=(
        "//*["
        "not(ancestor::nav)"
        " and "
        "contains("
        "translate("
        "normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ',"
        "'abcdefghijklmnopqrstuvwxyzáéíóú'"
        "),"
        "'registro presupuestal'"
        ")"
        "]"
    ),
    priority=20,
    description=(
        "Fallback mediante el texto Registro Presupuestal."
    ),
),
    LocatorSpec(
        key="budget.item_input",
        by=By.CSS_SELECTOR,
        value="input[name*='rubro']",
        priority=10,
        description="Rubro o ítem presupuestal.",
    ),
    LocatorSpec(
        key="budget.subsector_input",
        by=By.CSS_SELECTOR,
        value="input[name*='subsector']",
        priority=10,
        description="Subsector presupuestal.",
    ),
    LocatorSpec(
        key="budget.cdp_input",
        by=By.CSS_SELECTOR,
        value="input[name*='cdp']",
        priority=10,
        description="Número o código CDP.",
    ),
    LocatorSpec(
        key="budget.gross_total_input",
        by=By.CSS_SELECTOR,
        value="input[name*='valor']",
        priority=10,
        description="Valor bruto presupuestal.",
    ),
    LocatorSpec(
        key="budget.save_button",
        by=By.XPATH,
        value=(
            "//button["
            "contains(normalize-space(.),'Guardar')"
            "]"
        ),
        priority=10,
        description="Guarda la información presupuestal.",
    ),
)