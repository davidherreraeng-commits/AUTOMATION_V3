from __future__ import annotations

from adapters.portal.gestion_transparente.locators import (
    LocatorRegistry,
)
from adapters.portal.gestion_transparente.locators.profiles import (
    PortalLocatorProfile,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.budget_register_locators import (
    BUDGET_REGISTER_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.contract_header_locators import (
    CONTRACT_HEADER_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.contractor_locators import (
    CONTRACTOR_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.general_completion_locators import (
    GENERAL_COMPLETION_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.general_data_locators import (
    GENERAL_DATA_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.general_save_locators import (
    GENERAL_SAVE_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.navigation_locators import (
    NAVIGATION_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.project_locators import (
    PROJECT_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.supervisor_locators import (
    SUPERVISOR_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.availability_locators import (
    AVAILABILITY_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.additional_dates_locators import (
    ADDITIONAL_DATES_LOCATORS,
)

PROFILE_VERSION = "v2026_07"


REQUIRED_LOCATOR_KEYS: frozenset[str] = frozenset(
    {
        # Inicio de sesión y navegación.
        "portal.login.username",
        "portal.login.password",
        "portal.login.submit",
        "navigation.contracting_menu",
        "navigation.enter_contract",
        "assistant.open",
        "assistant.container",

        # Cabecera contractual.
        "contract.header.record_type_contract",
        "contract.header.contract_number",
        "contract.header.contractor_link",
        "contract.header.project_link",
        "contract.header.validate_button",
        "contract.header.validation_success",

        # Contratista.
        "contractor.dialog",
        "contractor.nature.legal",
        "contractor.nature.natural",
        "contractor.legal.id_type",
        "contractor.legal.document_input",
        "contractor.natural.id_type",
        "contractor.natural.document_input",
        "contractor.document_input",
        "contractor.search_button",
        "contractor.result_row",
        "contractor.confirm_button",

        # Proyecto.
        "project.dialog",
        "project.code_input",
        "project.search_button",
        "project.result_row",
        "project.confirm_button",

        # Datos generales principales.
        "general.object_description",
        "general.signing_date",
        "general.starting_date",
        "general.amount",
        "general.amount_in_words",
        "general.contract_term",
        "general.term_unit_days",
        "general.term_unit_months",
        "general.term_unit_years",
        "general.process_type",
        "general.typology",
        "general.contract_type",
        "general.other_currency_no",
        "general.other_currency_yes",

        # Finalización de datos generales.
        "general.government_plan",
        "general.budget_year",
        "general.budget_item",
        "general.budget_subsector",
        "general.budget_link_button",
        "general.secop_yes",
        "general.secop_no",
        "general.secop_url",
        "general.advance_no",
        "general.commercial_trust_no",
        "general.urgency_no",
        "general.future_commitment_no",
        "general.cooperation_contract_no",
        "general.execution_department",
        "general.execution_city",

        # Validación y guardado.
        "general.final_validate_button",
        "general.validation_success",
        "general.save_button",
        "general.save_success_dialog",
        "general.save_success_accept",
        "general.contract_saved",
        "supervisor.section",

        # Vinculación de interventor o supervisor.
        "supervisor.search_open",
        "supervisor.dialog",
        "supervisor.nature_person",
        "supervisor.id_type",
        "supervisor.document_input",
        "supervisor.search_button",
        "supervisor.result_row",
        "supervisor.select_button",
        "supervisor.selected_identifier",
        "supervisor.type_input",
        "supervisor.contract_input",
        "supervisor.validate_button",
        "supervisor.validation_success",
        "supervisor.link_button",
        "supervisor.link_success_dialog",
        "supervisor.link_success_accept",
        "supervisor.linked",
        "availability.section",

        # Registro presupuestal.
        "budget_register.number_input",
        "budget_register.date_input",
        "budget_register.availability_select",
        "budget_register.availability_option",
        "budget_register.gross_total_input",
        "budget_register.validate_button",
        "budget_register.validation_success",
        "budget_register.link_button",
        "budget_register.link_success_dialog",
        "budget_register.link_success_accept",
        "budget_register.linked",
        "additional_dates.section",

        # Disponibilidad presupuestal.
        "availability.search_input",
        "availability.available_row",
        "availability.cdp_cell",
        "availability.link_button",
        "availability.link_success",
        "availability.linked_section",
        "availability.linked_row",
        "availability.continue_button",
        "availability.linked",
        "budget_register.section",

        # Fechas adicionales.
        "additional_dates.opening_date_input",
        "additional_dates.guarantee_approval_date_input",
        "additional_dates.web_publication_date_input",
        "additional_dates.secop_publication_date_input",
        "additional_dates.calendar_dialog",
        "additional_dates.calendar_day_option",
        "additional_dates.validate_button",
        "additional_dates.skip_button",
        "additional_dates.validation_success",
        "additional_dates.link_button",
        "additional_dates.link_success_dialog",
        "additional_dates.link_success_accept",
        "additional_dates.linked",
        "file_reported.section",
    }
)

def build_profile() -> PortalLocatorProfile:
    return PortalLocatorProfile(
        version=PROFILE_VERSION,
        locators=(
            *NAVIGATION_LOCATORS,
            *CONTRACT_HEADER_LOCATORS,
            *CONTRACTOR_LOCATORS,
            *PROJECT_LOCATORS,
            *GENERAL_DATA_LOCATORS,
            *GENERAL_COMPLETION_LOCATORS,
            *GENERAL_SAVE_LOCATORS,
            *SUPERVISOR_LOCATORS,
            *AVAILABILITY_LOCATORS,
            *BUDGET_REGISTER_LOCATORS,
            *ADDITIONAL_DATES_LOCATORS,
        ),
        required_keys=REQUIRED_LOCATOR_KEYS,
    )

def build_registry() -> LocatorRegistry:
    return build_profile().build_registry()