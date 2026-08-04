from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_scope_availability_search_input() -> None:
    candidate = build_registry().candidates(
        "availability.search_input"
    )[0]

    assert "Seleccione la Disponibilidad" in candidate.value
    assert "input[@id='search'][1]" in candidate.value


def test_should_register_available_rows_and_cdp_cells() -> None:
    registry = build_registry()

    row = registry.candidates(
        "availability.available_row"
    )[0].value

    cdp = registry.candidates(
        "availability.cdp_cell"
    )[0].value

    assert "@role='row' and @data-id" in row
    assert "BUDGET_AVAILABILITY_IDENTIFIER" in cdp


def test_should_scope_link_button_to_available_grid() -> None:
    candidate = build_registry().candidates(
        "availability.link_button"
    )[0]

    assert "Seleccione la Disponibilidad" in candidate.value
    assert "button[@title='Vincular']" in candidate.value


def test_should_register_link_success_notification() -> None:
    candidate = build_registry().candidates(
        "availability.link_success"
    )[0]

    assert "@role='status'" in candidate.value
    assert (
        "Se ha vinculado la disponibilidad "
        "presupuestal exitosamente"
        in candidate.value
    )


def test_should_register_persistent_linked_row() -> None:
    registry = build_registry()

    section = registry.candidates(
        "availability.linked_section"
    )[0].value

    row = registry.candidates(
        "availability.linked_row"
    )[0].value

    assert "Disponibilidades Vinculadas" in section
    assert "Disponibilidades Vinculadas" in row
    assert "@role='row' and @data-id" in row


def test_should_register_continue_button() -> None:
    candidate = build_registry().candidates(
        "availability.continue_button"
    )[0]

    assert (
        candidate.value
        == "//button[normalize-space()='Continuar']"
    )


def test_should_register_budget_register_transition() -> None:
    registry = build_registry()

    linked = registry.candidates(
        "availability.linked"
    )

    budget_register = registry.candidates(
        "budget_register.section"
    )

    assert (
        "RETIRAR REGISTRO PRESUPUESTAL"
        in linked[0].value
    )
    assert (
        linked[1].value
        == "input[name='budgetRegister.0.register']"
    )

    assert linked[0].value == budget_register[0].value
    assert linked[1].value == budget_register[1].value