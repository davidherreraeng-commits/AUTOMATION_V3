<<<<<<< HEAD
from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_register_general_text_fields() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.object_description"
        )[0].value
        == "textarea[name='objectDesc']"
    )

    assert (
        registry.candidates(
            "general.amount"
        )[0].value
        == "input[name='amount']"
    )

    assert (
        registry.candidates(
            "general.amount_in_words"
        )[0].value
        == "input[name='amountLetter']"
    )

    assert (
        registry.candidates(
            "general.contract_term"
        )[0].value
        == "input[name='contractTermDays']"
    )


def test_should_register_general_date_fields() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.signing_date"
        )[0].value
        == "input#signingDate"
    )

    assert (
        registry.candidates(
            "general.starting_date"
        )[0].value
        == "input#startingDate"
    )


def test_should_register_distinct_term_units() -> None:
    registry = build_registry()

    days = registry.candidates(
        "general.term_unit_days"
    )[0].value

    months = registry.candidates(
        "general.term_unit_months"
    )[0].value

    years = registry.candidates(
        "general.term_unit_years"
    )[0].value

    assert "[value='1']" in days
    assert "[value='2']" in months
    assert "[value='3']" in years

    assert len(
        {
            days,
            months,
            years,
        }
    ) == 3


def test_should_register_contract_classification_fields() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.process_type"
        )[0].value
        == "input#processType"
    )

    assert (
        registry.candidates(
            "general.typology"
        )[0].value
        == "input#typology"
    )

    assert (
        registry.candidates(
            "general.contract_type"
        )[0].value
        == "input#type"
    )


def test_should_register_distinct_currency_options() -> None:
    registry = build_registry()

    no_option = registry.candidates(
        "general.other_currency_no"
    )[0].value

    yes_option = registry.candidates(
        "general.other_currency_yes"
    )[0].value

    assert "[value='NO']" in no_option
    assert "[value='SI']" in yes_option
=======
from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_register_general_text_fields() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.object_description"
        )[0].value
        == "textarea[name='objectDesc']"
    )

    assert (
        registry.candidates(
            "general.amount"
        )[0].value
        == "input[name='amount']"
    )

    assert (
        registry.candidates(
            "general.amount_in_words"
        )[0].value
        == "input[name='amountLetter']"
    )

    assert (
        registry.candidates(
            "general.contract_term"
        )[0].value
        == "input[name='contractTermDays']"
    )


def test_should_register_general_date_fields() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.signing_date"
        )[0].value
        == "input#signingDate"
    )

    assert (
        registry.candidates(
            "general.starting_date"
        )[0].value
        == "input#startingDate"
    )


def test_should_register_distinct_term_units() -> None:
    registry = build_registry()

    days = registry.candidates(
        "general.term_unit_days"
    )[0].value

    months = registry.candidates(
        "general.term_unit_months"
    )[0].value

    years = registry.candidates(
        "general.term_unit_years"
    )[0].value

    assert "[value='1']" in days
    assert "[value='2']" in months
    assert "[value='3']" in years

    assert len(
        {
            days,
            months,
            years,
        }
    ) == 3


def test_should_register_contract_classification_fields() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.process_type"
        )[0].value
        == "input#processType"
    )

    assert (
        registry.candidates(
            "general.typology"
        )[0].value
        == "input#typology"
    )

    assert (
        registry.candidates(
            "general.contract_type"
        )[0].value
        == "input#type"
    )


def test_should_register_distinct_currency_options() -> None:
    registry = build_registry()

    no_option = registry.candidates(
        "general.other_currency_no"
    )[0].value

    yes_option = registry.candidates(
        "general.other_currency_yes"
    )[0].value

    assert "[value='NO']" in no_option
    assert "[value='SI']" in yes_option
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
    assert no_option != yes_option