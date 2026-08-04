from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_register_number_and_gross_total() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "budget_register.number_input"
        )[0].value
        == "input[name='budgetRegister.0.register']"
    )

    assert (
        registry.candidates(
            "budget_register.gross_total_input"
        )[0].value
        == (
            "input[name="
            "'budgetRegister[0].availability[0].amount'"
            "]"
        )
    )


def test_should_register_date_using_stable_label() -> None:
    candidate = build_registry().candidates(
        "budget_register.date_input"
    )[0]

    assert "Fecha Registro Presupuestal" in candidate.value
    assert "/following::input[1]" in candidate.value


def test_should_register_availability_select_and_option() -> None:
    registry = build_registry()

    select_candidate = registry.candidates(
        "budget_register.availability_select"
    )[0].value

    option_candidate = registry.candidates(
        "budget_register.availability_option"
    )[0].value

    assert (
        "budgetRegister[0].availability[0].value"
        in select_candidate
    )
    assert "@role='combobox'" in select_candidate

    assert "@role='listbox'" in option_candidate
    assert "@role='option'" in option_candidate
    assert "@data-value" in option_candidate


def test_should_scope_validate_to_budget_register_card() -> None:
    candidates = build_registry().candidates(
        "budget_register.validate_button"
    )

    assert len(candidates) == 2
    assert "budgetRegister.0.register" in candidates[0].value
    assert "MuiCard-root" in candidates[0].value
    assert "Validar" in candidates[0].value

    assert (
        "RETIRAR REGISTRO PRESUPUESTAL"
        in candidates[1].value
    )


def test_should_use_link_as_validation_postcondition() -> None:
    registry = build_registry()

    validation = registry.candidates(
        "budget_register.validation_success"
    )

    link = registry.candidates(
        "budget_register.link_button"
    )

    assert len(validation) == 2
    assert len(link) == 2

    assert "MuiCard-root" in validation[0].value
    assert "Vincular" in validation[0].value

    assert validation[0].value == link[0].value
    assert validation[1].value == link[1].value


def test_should_register_link_success_dialog() -> None:
    registry = build_registry()

    dialog = registry.candidates(
        "budget_register.link_success_dialog"
    )[0].value

    accept = registry.candidates(
        "budget_register.link_success_accept"
    )[0].value

    assert (
        "Se ha vinculado el registro presupuestal "
        "al contrato exitosamente"
        in dialog
    )
    assert "Aceptar" in accept


def test_should_register_additional_dates_transition() -> None:
    registry = build_registry()

    linked = registry.candidates(
        "budget_register.linked"
    )

    additional_dates = registry.candidates(
        "additional_dates.section"
    )

    assert len(linked) == 2
    assert len(additional_dates) == 2

    assert "VINCULAR FECHAS" in linked[0].value
    assert (
        linked[1].value
        == "input[name='additionalDates.0.value']"
    )

    assert linked[0].value == additional_dates[0].value
    assert linked[1].value == additional_dates[1].value