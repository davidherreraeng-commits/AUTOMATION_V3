from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    REQUIRED_LOCATOR_KEYS,
    V2026_07_HEALTH_CHECK_PHASES,
)


def test_should_cover_all_required_keys_once() -> None:
    planned_keys = tuple(
        key
        for phase in V2026_07_HEALTH_CHECK_PHASES
        for key in phase.keys
    )

    assert len(V2026_07_HEALTH_CHECK_PHASES) == 22
    assert len(planned_keys) == 64
    assert len(set(planned_keys)) == 64

    assert set(planned_keys) == set(REQUIRED_LOCATOR_KEYS)


def test_should_separate_contractual_dialogs() -> None:
    phases = {
        phase.name: set(phase.keys)
        for phase in V2026_07_HEALTH_CHECK_PHASES
    }

    assert phases["contractor_legal"] == {
        "contractor.legal.id_type",
        "contractor.legal.document_input",
        "contractor.document_input",
        "contractor.search_button",
    }

    assert phases["project_dialog"] == {
        "project.dialog",
        "project.code_input",
        "project.search_button",
    }

    assert phases["general_core_data"] == {
        "general.object_description",
        "general.signing_date",
        "general.starting_date",
        "general.amount",
        "general.amount_in_words",
        "general.contract_term",
        "general.term_unit_days",
        "general.term_unit_months",
        "general.term_unit_years",
    }

    assert phases["general_classification"] == {
        "general.process_type",
        "general.typology",
        "general.contract_type",
        "general.other_currency_no",
        "general.other_currency_yes",
    }


def test_should_separate_general_completion_sections() -> None:
    phases = {
        phase.name: set(phase.keys)
        for phase in V2026_07_HEALTH_CHECK_PHASES
    }

    assert phases["general_government_plan"] == {
        "general.government_plan",
    }

    assert phases["general_budget_year"] == {
        "general.budget_year",
    }

    assert phases["general_budget_item"] == {
        "general.budget_item",
    }

    assert phases["general_budget_linkage"] == {
        "general.budget_subsector",
        "general.budget_link_button",
    }

    assert phases["general_secop_controls"] == {
        "general.secop_yes",
        "general.secop_no",
    }

    assert phases["general_secop_url_and_flags"] == {
        "general.secop_url",
        "general.advance_no",
        "general.commercial_trust_no",
        "general.urgency_no",
        "general.future_commitment_no",
        "general.cooperation_contract_no",
    }

    assert phases["general_execution_location"] == {
        "general.execution_department",
        "general.execution_city",
    }


def test_should_separate_legal_and_natural_contractors() -> None:
    phases = {
        phase.name: set(phase.keys)
        for phase in V2026_07_HEALTH_CHECK_PHASES
    }

    assert phases["contractor_natural"] == {
        "contractor.natural.id_type",
        "contractor.natural.document_input",
    }

    assert (
        "contractor.legal.document_input"
        not in phases["contractor_natural"]
    )

    assert (
        "contractor.natural.document_input"
        not in phases["contractor_legal"]
    )