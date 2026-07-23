from __future__ import annotations

from adapters.portal.gestion_transparente.locators import (
    LocatorRegistry,
)
from adapters.portal.gestion_transparente.locators.profiles import (
    PortalLocatorProfile,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.budget_locators import (
    BUDGET_LOCATORS,
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
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.navigation_locators import (
    NAVIGATION_LOCATORS,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07.project_locators import (
    PROJECT_LOCATORS,
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

        # Terminación de datos generales.
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

        # Presupuesto posterior.
        "budget.section",
        "budget.item_input",
        "budget.subsector_input",
        "budget.cdp_input",
        "budget.gross_total_input",
        "budget.save_button",
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
            *BUDGET_LOCATORS,
        ),
        required_keys=REQUIRED_LOCATOR_KEYS,
    )


def build_registry() -> LocatorRegistry:
    return build_profile().build_registry()