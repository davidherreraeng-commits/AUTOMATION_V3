from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_register_additional_dates_section() -> None:
    candidates = build_registry().candidates(
        "additional_dates.section"
    )

    assert len(candidates) == 2
    assert "VINCULAR FECHAS" in candidates[0].value
    assert (
        candidates[1].value
        == "input[name='additionalDates.0.value']"
    )


def test_should_register_four_fixed_date_fields() -> None:
    registry = build_registry()

    expected = {
        "additional_dates.opening_date_input":
            "input[name='additionalDates.0.value']",
        "additional_dates.guarantee_approval_date_input":
            "input[name='additionalDates.1.value']",
        "additional_dates.web_publication_date_input":
            "input[name='additionalDates.2.value']",
        "additional_dates.secop_publication_date_input":
            "input[name='additionalDates.3.value']",
    }

    for key, value in expected.items():
        assert registry.candidates(key)[0].value == value


def test_should_register_react_datepicker() -> None:
    registry = build_registry()

    dialog = registry.candidates(
        "additional_dates.calendar_dialog"
    )[0].value

    day = registry.candidates(
        "additional_dates.calendar_day_option"
    )[0].value

    assert "@aria-label='Choose Date'" in dialog
    assert "@role='option'" in day
    assert "@aria-label" in day


def test_should_scope_validate_and_skip_to_dates_card() -> None:
    registry = build_registry()

    validate = registry.candidates(
        "additional_dates.validate_button"
    )

    skip = registry.candidates(
        "additional_dates.skip_button"
    )

    assert len(validate) == 2
    assert len(skip) == 2

    assert "additionalDates.0.value" in validate[0].value
    assert "MuiCard-root" in validate[0].value
    assert "Validar" in validate[0].value

    assert "additionalDates.0.value" in skip[0].value
    assert "MuiCard-root" in skip[0].value
    assert "Saltar Paso" in skip[0].value


def test_should_use_link_as_validation_postcondition() -> None:
    registry = build_registry()

    validation = registry.candidates(
        "additional_dates.validation_success"
    )

    link = registry.candidates(
        "additional_dates.link_button"
    )

    assert len(validation) == 2
    assert len(link) == 2

    assert validation[0].value == link[0].value
    assert validation[1].value == link[1].value

    assert "MuiCard-root" in validation[0].value
    assert "Vincular" in validation[0].value


def test_should_register_link_success_dialog() -> None:
    registry = build_registry()

    dialog = registry.candidates(
        "additional_dates.link_success_dialog"
    )[0].value

    accept = registry.candidates(
        "additional_dates.link_success_accept"
    )[0].value

    assert (
        "Se han vinculado las fechas adicionales "
        "al contrato exitosamente"
        in dialog
    )
    assert "Aceptar" in accept


def test_should_register_file_reported_transition() -> None:
    registry = build_registry()

    linked = registry.candidates(
        "additional_dates.linked"
    )

    file_reported = registry.candidates(
        "file_reported.section"
    )

    assert len(linked) == 2
    assert len(file_reported) == 2

    assert "VINCULAR ANEXOS" in linked[0].value
    assert linked[1].value == "input[type='file']"

    assert linked[0].value == file_reported[0].value
    assert linked[1].value == file_reported[1].value