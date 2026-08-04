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

    assert len(V2026_07_HEALTH_CHECK_PHASES) == 48
    assert len(planned_keys) == 119
    assert len(set(planned_keys)) == 119

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

def test_should_separate_general_save_states() -> None:
    phases = {
        phase.name: set(phase.keys)
        for phase in V2026_07_HEALTH_CHECK_PHASES
    }

    assert phases["general_final_validation"] == {
        "general.final_validate_button",
    }

    assert phases["general_validation_result"] == {
        "general.validation_success",
        "general.save_button",
    }

    assert phases["general_save_success"] == {
        "general.save_success_dialog",
        "general.save_success_accept",
    }

    assert phases["supervisor_transition"] == {
        "general.contract_saved",
        "supervisor.section",
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

def test_should_separate_supervisor_flow() -> None:
    phases = {
        phase.name: set(phase.keys)
        for phase in V2026_07_HEALTH_CHECK_PHASES
    }

    assert phases["supervisor_initial_controls"] == {
        "supervisor.search_open",
    }

    assert phases["supervisor_search_dialog"] == {
        "supervisor.dialog",
        "supervisor.nature_person",
    }

    assert phases["supervisor_person_fields"] == {
        "supervisor.id_type",
        "supervisor.document_input",
        "supervisor.search_button",
    }

    assert phases["supervisor_search_results"] == {
        "supervisor.result_row",
        "supervisor.select_button",
    }

    assert phases["supervisor_selected"] == {
        "supervisor.selected_identifier",
        "supervisor.type_input",
        "supervisor.contract_input",
        "supervisor.validate_button",
    }

    assert phases["supervisor_validation_result"] == {
        "supervisor.validation_success",
        "supervisor.link_button",
    }

    assert phases["supervisor_link_success"] == {
        "supervisor.link_success_dialog",
        "supervisor.link_success_accept",
    }

    assert phases["availability_transition"] == {
        "supervisor.linked",
        "availability.section",
    }

def test_should_separate_availability_flow() -> None:
    phases = {
        phase.name: set(phase.keys)
        for phase in V2026_07_HEALTH_CHECK_PHASES
    }

    assert phases["availability_initial_controls"] == {
        "availability.search_input",
    }

    assert phases["availability_target_result"] == {
        "availability.available_row",
        "availability.cdp_cell",
        "availability.link_button",
    }

    assert phases["availability_link_result"] == {
        "availability.link_success",
        "availability.linked_section",
        "availability.linked_row",
    }

    assert phases["availability_continue"] == {
        "availability.continue_button",
    }

    assert phases["budget_register_transition"] == {
        "availability.linked",
        "budget_register.section",
    }

def test_should_separate_budget_register_flow() -> None:
    phases = {
        phase.name: set(phase.keys)
        for phase in V2026_07_HEALTH_CHECK_PHASES
    }

    assert phases["budget_register_initial_controls"] == {
        "budget_register.number_input",
        "budget_register.date_input",
        "budget_register.availability_select",
        "budget_register.gross_total_input",
        "budget_register.validate_button",
    }

    assert phases["budget_register_availability_options"] == {
        "budget_register.availability_option",
    }

    assert phases["budget_register_validation_result"] == {
        "budget_register.validation_success",
        "budget_register.link_button",
    }

    assert phases["budget_register_link_success"] == {
        "budget_register.link_success_dialog",
        "budget_register.link_success_accept",
    }

    assert phases["additional_dates_transition"] == {
        "budget_register.linked",
        "additional_dates.section",
    }

def test_should_separate_additional_dates_flow() -> None:
    phases = {
        phase.name: set(phase.keys)
        for phase in V2026_07_HEALTH_CHECK_PHASES
    }

    assert phases["additional_dates_initial_controls"] == {
        "additional_dates.opening_date_input",
        "additional_dates.guarantee_approval_date_input",
        "additional_dates.web_publication_date_input",
        "additional_dates.secop_publication_date_input",
        "additional_dates.validate_button",
        "additional_dates.skip_button",
    }

    assert phases["additional_dates_calendar"] == {
        "additional_dates.calendar_dialog",
        "additional_dates.calendar_day_option",
    }

    assert phases["additional_dates_validation_result"] == {
        "additional_dates.validation_success",
        "additional_dates.link_button",
    }

    assert phases["additional_dates_link_success"] == {
        "additional_dates.link_success_dialog",
        "additional_dates.link_success_accept",
    }

    assert phases["file_reported_transition"] == {
        "additional_dates.linked",
        "file_reported.section",
    }