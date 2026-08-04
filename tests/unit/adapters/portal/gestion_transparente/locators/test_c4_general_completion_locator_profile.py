<<<<<<< HEAD
from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_register_budget_classification_fields() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.government_plan"
        )[0].value
        == "input#budgetDevPlan"
    )

    assert (
        registry.candidates(
            "general.budget_year"
        )[0].value
        == "input#budgetYear"
    )

    assert (
        registry.candidates(
            "general.budget_item"
        )[0].value
        == "input#budgetItem"
    )

    assert (
        registry.candidates(
            "general.budget_subsector"
        )[0].value
        == "input#budgetExpenditureSubSector"
    )


def test_should_register_budget_link_button() -> None:
    candidate = build_registry().candidates(
        "general.budget_link_button"
    )[0]

    assert "budgetExpenditureSubSector" in candidate.value
    assert "Vincular" in candidate.value


def test_should_register_secop_controls() -> None:
    registry = build_registry()

    secop_yes = registry.candidates(
        "general.secop_yes"
    )[0].value

    secop_no = registry.candidates(
        "general.secop_no"
    )[0].value

    assert "secopPublication" in secop_yes
    assert "[value='SI']" in secop_yes
    assert "[value='NO']" in secop_no

    assert (
        registry.candidates(
            "general.secop_url"
        )[0].value
        == "input[name='secopURL']"
    )


def test_should_register_negative_contract_flags() -> None:
    registry = build_registry()

    expected_names = {
        "general.advance_no": "advanceDefined",
        "general.commercial_trust_no": "commercialTrust",
        "general.urgency_no": "urgencyManifest",
        "general.future_commitment_no": "validityFuture",
        "general.cooperation_contract_no": "cooperationContract",
    }

    for key, expected_name in expected_names.items():
        value = registry.candidates(key)[0].value

        assert expected_name in value
        assert "[value='NO']" in value


def test_should_register_execution_location() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.execution_department"
        )[0].value
        == "input#executionProvince"
    )

    assert (
        registry.candidates(
            "general.execution_city"
        )[0].value
        == "input#executionCity"
=======
from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_register_budget_classification_fields() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.government_plan"
        )[0].value
        == "input#budgetDevPlan"
    )

    assert (
        registry.candidates(
            "general.budget_year"
        )[0].value
        == "input#budgetYear"
    )

    assert (
        registry.candidates(
            "general.budget_item"
        )[0].value
        == "input#budgetItem"
    )

    assert (
        registry.candidates(
            "general.budget_subsector"
        )[0].value
        == "input#budgetExpenditureSubSector"
    )


def test_should_register_budget_link_button() -> None:
    candidate = build_registry().candidates(
        "general.budget_link_button"
    )[0]

    assert "budgetExpenditureSubSector" in candidate.value
    assert "Vincular" in candidate.value


def test_should_register_secop_controls() -> None:
    registry = build_registry()

    secop_yes = registry.candidates(
        "general.secop_yes"
    )[0].value

    secop_no = registry.candidates(
        "general.secop_no"
    )[0].value

    assert "secopPublication" in secop_yes
    assert "[value='SI']" in secop_yes
    assert "[value='NO']" in secop_no

    assert (
        registry.candidates(
            "general.secop_url"
        )[0].value
        == "input[name='secopURL']"
    )


def test_should_register_negative_contract_flags() -> None:
    registry = build_registry()

    expected_names = {
        "general.advance_no": "advanceDefined",
        "general.commercial_trust_no": "commercialTrust",
        "general.urgency_no": "urgencyManifest",
        "general.future_commitment_no": "validityFuture",
        "general.cooperation_contract_no": "cooperationContract",
    }

    for key, expected_name in expected_names.items():
        value = registry.candidates(key)[0].value

        assert expected_name in value
        assert "[value='NO']" in value


def test_should_register_execution_location() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "general.execution_department"
        )[0].value
        == "input#executionProvince"
    )

    assert (
        registry.candidates(
            "general.execution_city"
        )[0].value
        == "input#executionCity"
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
    )