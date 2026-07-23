from __future__ import annotations

from adapters.portal.gestion_transparente.locators.contract_tests.interactive_health_check import (
    PortalHealthCheckPhase,
)


V2026_07_HEALTH_CHECK_PHASES: tuple[
    PortalHealthCheckPhase,
    ...
] = (
    PortalHealthCheckPhase(
        name="login_page",
        label="Inicio de sesión",
        instructions=(
            "Ubica Chrome en la pantalla de autenticación."
        ),
        keys=(
            "portal.login.username",
            "portal.login.password",
            "portal.login.submit",
        ),
    ),
    PortalHealthCheckPhase(
        name="contracting_menu",
        label="Menú Contratación",
        instructions=(
            "Inicia sesión y ubica el menú lateral "
            "Contratación antes de expandirlo."
        ),
        keys=(
            "navigation.contracting_menu",
        ),
    ),
    PortalHealthCheckPhase(
        name="enter_contract",
        label="Submenú Ingresar Contrato",
        instructions=(
            "Expande Contratación y ubica "
            "Ingresar Contrato."
        ),
        keys=(
            "navigation.enter_contract",
        ),
    ),
    PortalHealthCheckPhase(
        name="assistant_access",
        label="Acceso al Asistente",
        instructions=(
            "Expande Ingresar Contrato y ubica "
            "Asistente de Contratación."
        ),
        keys=(
            "assistant.open",
        ),
    ),
    PortalHealthCheckPhase(
        name="assistant_header",
        label="Inicio del nuevo contrato",
        instructions=(
            "Abre el asistente. Deben verse el radio Contrato, "
            "Número, búsquedas de contratista y proyecto, "
            "y el botón Validar."
        ),
        keys=(
            "assistant.container",
            "contract.header.record_type_contract",
            "contract.header.contract_number",
            "contract.header.contractor_link",
            "contract.header.project_link",
            "contract.header.validate_button",
        ),
    ),
    PortalHealthCheckPhase(
        name="contractor_dialog",
        label="Diálogo de contratistas",
        instructions=(
            "Abre la búsqueda de contratistas. "
            "No selecciones todavía una naturaleza."
        ),
        keys=(
            "contractor.dialog",
            "contractor.nature.legal",
            "contractor.nature.natural",
        ),
    ),
    PortalHealthCheckPhase(
        name="contractor_legal",
        label="Contratista jurídico",
        instructions=(
            "Selecciona Jurídica. Deben verse el tipo de "
            "identificación, NIT y Buscar."
        ),
        keys=(
            "contractor.legal.id_type",
            "contractor.legal.document_input",
            "contractor.document_input",
            "contractor.search_button",
        ),
    ),
    PortalHealthCheckPhase(
        name="contractor_results",
        label="Resultado del contratista",
        instructions=(
            "Selecciona NIT, realiza una búsqueda autorizada "
            "y espera hasta ver una coincidencia y el botón "
            "Seleccionar."
        ),
        keys=(
            "contractor.result_row",
            "contractor.confirm_button",
        ),
    ),
    PortalHealthCheckPhase(
        name="contractor_natural",
        label="Contratista natural",
        instructions=(
            "Vuelve al formulario de búsqueda y selecciona "
            "Natural. Deben verse Tipo de Identificación e "
            "Identificación. No es necesario buscar."
        ),
        keys=(
            "contractor.natural.id_type",
            "contractor.natural.document_input",
        ),
    ),
    PortalHealthCheckPhase(
        name="project_dialog",
        label="Diálogo de proyectos",
        instructions=(
            "Cierra el diálogo de contratistas, abre Proyecto "
            "y ubica Código del Proyecto y Buscar."
        ),
        keys=(
            "project.dialog",
            "project.code_input",
            "project.search_button",
        ),
    ),
    PortalHealthCheckPhase(
        name="project_results",
        label="Resultado del proyecto",
        instructions=(
            "Busca un código autorizado y espera hasta ver "
            "la fila coincidente y el botón Seleccionar."
        ),
        keys=(
            "project.result_row",
            "project.confirm_button",
        ),
    ),
    PortalHealthCheckPhase(
        name="header_validation_result",
        label="Cabecera validada y datos generales habilitados",
        instructions=(
            "Selecciona definitivamente el contratista y el "
            "proyecto. Pulsa Validar y espera hasta que aparezcan "
            "los datos generales."
        ),
        keys=(
            "contract.header.validation_success",
        ),
    ),
    PortalHealthCheckPhase(
        name="general_core_data",
        label="Datos generales principales",
        instructions=(
            "Después de validar la cabecera, ubica Objeto del "
            "Contrato, Fecha Suscripción, Fecha Inicio, Valor, "
            "Valor en Letras, Plazo Estimado y las unidades "
            "Días, Meses y Años. No ingreses ni modifiques datos."
        ),
        keys=(
            "general.object_description",
            "general.signing_date",
            "general.starting_date",
            "general.amount",
            "general.amount_in_words",
            "general.contract_term",
            "general.term_unit_days",
            "general.term_unit_months",
            "general.term_unit_years",
        ),
    ),
    PortalHealthCheckPhase(
        name="general_classification",
        label="Clasificación contractual y moneda",
        instructions=(
            "Haz scroll hasta Modalidad o Proceso, Procedimiento "
            "o Causal, Tipo de Contrato y Se Pactó en Moneda "
            "Extranjera. No selecciones opciones todavía."
        ),
        keys=(
            "general.process_type",
            "general.typology",
            "general.contract_type",
            "general.other_currency_no",
            "general.other_currency_yes",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_government_plan",
    label="Plan de Gobierno",
    instructions=(
        "Ubica Plan de Gobierno. Selecciona manualmente el "
        "plan correspondiente y espera hasta que se habilite "
        "Año al que aplica el Rubro. Presiona Enter después "
        "de que el año aparezca."
    ),
    keys=(
        "general.government_plan",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_budget_year",
    label="Año del rubro presupuestal",
    instructions=(
        "Ubica Año al que aplica el Rubro. Selecciona "
        "manualmente el año correspondiente y espera hasta "
        "que aparezca Rubro Presupuestal. Presiona Enter "
        "después de que el rubro aparezca."
    ),
    keys=(
        "general.budget_year",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_budget_item",
    label="Rubro presupuestal",
    instructions=(
        "Ubica Rubro Presupuestal. Selecciona manualmente el "
        "rubro correspondiente y espera hasta que aparezcan "
        "Sub-Sector y el botón Vincular. Presiona Enter "
        "después de que ambos estén visibles."
    ),
    keys=(
        "general.budget_item",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_budget_linkage",
    label="Subsector y vinculación presupuestal",
    instructions=(
        "Ubica Sub-Sector y el botón Vincular. Selecciona el "
        "subsector correspondiente cuando sea obligatorio, "
        "pero no pulses Vincular durante esta comprobación. "
        "Presiona Enter cuando ambos controles estén visibles."
    ),
    keys=(
        "general.budget_subsector",
        "general.budget_link_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_secop_controls",
    label="Publicación en SECOP",
    instructions=(
        "Ubica las opciones No y Sí de Se Publicó en el SECOP. "
        "Selecciona manualmente Sí y espera hasta que aparezca "
        "el campo URL del Contrato en el SECOP. Presiona Enter "
        "después de que el campo URL esté visible."
    ),
    keys=(
        "general.secop_yes",
        "general.secop_no",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_secop_url_and_flags",
    label="URL SECOP e indicadores contractuales",
    instructions=(
        "Con SECOP marcado en Sí, ubica el campo URL, Anticipo, "
        "Fiducia Mercantil, Urgencia Manifiesta, Vigencia "
        "Futura y Es Convenio. No es necesario escribir la URL "
        "ni modificar los demás indicadores."
    ),
    keys=(
        "general.secop_url",
        "general.advance_no",
        "general.commercial_trust_no",
        "general.urgency_no",
        "general.future_commitment_no",
        "general.cooperation_contract_no",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_execution_location",
    label="Ubicación de ejecución",
    instructions=(
        "Haz scroll hasta Departamento de Ejecución y "
        "Municipio de Ejecución. No selecciones Antioquia "
        "ni Medellín todavía."
    ),
    keys=(
        "general.execution_department",
        "general.execution_city",
        ),
    ),
    PortalHealthCheckPhase(
        name="budget_section",
        label="Presupuesto posterior",
        instructions=(
            "Esta fase pertenece a un incremento posterior. "
            "Selecciona S por ahora."
        ),
        keys=(
            "budget.section",
            "budget.item_input",
            "budget.subsector_input",
            "budget.cdp_input",
            "budget.gross_total_input",
            "budget.save_button",
        ),
    ),
)