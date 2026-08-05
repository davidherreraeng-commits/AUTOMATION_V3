from __future__ import annotations

import pytest

from application.services.gestion_transparente_catalog import (
    CONTRACT_TYPE,
    PROCESS_TYPE,
    PROCEDURE,
    CatalogValueNotFoundError,
    default_gt_catalog,
)


def test_should_preserve_exact_portal_values() -> None:
    catalog = default_gt_catalog()

    assert catalog.resolve(
        PROCESS_TYPE,
        "Contratacion Directa",
    ) == "Contratacion Directa"
    assert catalog.resolve(
        PROCEDURE,
        "Sin Pluraridad de Oferentes",
    ) == "Sin Pluraridad de Oferentes"
    assert catalog.resolve(
        CONTRACT_TYPE,
        "Contrato de Prestación de Servicios",
    ) == "Contrato de Prestación de Servicios"


def test_should_resolve_only_explicit_approved_aliases() -> None:
    catalog = default_gt_catalog()

    assert catalog.resolve(
        PROCEDURE,
        "Sin Pluralidad De Oferentes",
    ) == "Sin Pluraridad de Oferentes"
    assert catalog.resolve(
        PROCEDURE,
        "Prestación de Servicios",
    ) == "Prestación De Servicios Contratación Directa"
    assert catalog.resolve(
        CONTRACT_TYPE,
        "Servicios",
    ) == "Contrato de Prestación de Servicios"


def test_should_ignore_case_accents_and_repeated_spaces() -> None:
    catalog = default_gt_catalog()

    assert catalog.resolve(
        PROCESS_TYPE,
        "  CONTRATACIÓN   DIRECTA ",
    ) == "Contratacion Directa"


def test_should_reject_unknown_value_without_fuzzy_matching() -> None:
    catalog = default_gt_catalog()

    with pytest.raises(CatalogValueNotFoundError) as captured:
        catalog.resolve(PROCEDURE, "Pluralidad de proponentes")

    assert captured.value.field == PROCEDURE
    assert "Sin Pluraridad de Oferentes" in captured.value.allowed_values
