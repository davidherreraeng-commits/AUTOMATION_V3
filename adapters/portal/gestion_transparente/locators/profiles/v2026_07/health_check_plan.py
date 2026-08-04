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
    name="general_final_validation",
    label="Validación final de datos generales",
    instructions=(
        "Completa todos los datos obligatorios y verifica que "
        "la clasificación presupuestal esté vinculada. Deja "
        "visible el segundo botón Validar y presiona Enter "
        "antes de pulsarlo."
    ),
    keys=(
        "general.final_validate_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_validation_result",
    label="Datos generales validados",
    instructions=(
        "Pulsa el segundo botón Validar y espera hasta que "
        "desaparezca y sea reemplazado por Guardar y Volver. "
        "Presiona Enter cuando Guardar esté visible."
    ),
    keys=(
        "general.validation_success",
        "general.save_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="general_save_success",
    label="Contrato registrado exitosamente",
    instructions=(
        "Pulsa Guardar y espera el diálogo Éxito con el mensaje "
        "Se ha registrado el contrato exitosamente. No pulses "
        "Aceptar todavía. Presiona Enter con el diálogo abierto."
    ),
    keys=(
        "general.save_success_dialog",
        "general.save_success_accept",
        ),
    ),
    PortalHealthCheckPhase(
    name="supervisor_transition",
    label="Transición a interventor o supervisor",
    instructions=(
        "Pulsa Aceptar en el diálogo de éxito y espera hasta "
        "que aparezca VINCULAR INTERVENTOR/SUPERVISOR / "
        "NUEVO CONTRATO. Presiona Enter en esa pantalla."
    ),
    keys=(
        "general.contract_saved",
        "supervisor.section",
        ),
    ),
    PortalHealthCheckPhase(
    name="supervisor_initial_controls",
    label="Inicio de interventor o supervisor",
    instructions=(
        "En la pantalla VINCULAR INTERVENTOR/SUPERVISOR, "
        "ubica el botón Buscar Interventor / Supervisor. "
        "No lo pulses hasta que esta fase sea comprobada."
    ),
    keys=(
        "supervisor.search_open",
        ),
    ),
    PortalHealthCheckPhase(
    name="supervisor_search_dialog",
    label="Diálogo de interventores",
    instructions=(
        "Abre Buscar Interventor / Supervisor. Deben verse "
        "el diálogo Interventores y la opción Persona. "
        "No selecciones Persona todavía."
    ),
    keys=(
        "supervisor.dialog",
        "supervisor.nature_person",
        ),
    ),
    PortalHealthCheckPhase(
    name="supervisor_person_fields",
    label="Identificación del supervisor",
    instructions=(
        "Selecciona Persona. Deben aparecer Tipo de "
        "Identificación e Identificación. Selecciona el "
        "tipo correspondiente e ingresa una cédula "
        "autorizada. Pulsa BUSCAR y espera a que aparezca "
        "la lista de coincidencias."
    ),
    keys=(
        "supervisor.id_type",
        "supervisor.document_input",
        "supervisor.search_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="supervisor_search_results",
    label="Coincidencia del supervisor",
    instructions=(
        "Espera hasta que aparezca la coincidencia exacta "
        "en Lista de Coincidencias y el botón Seleccionar. "
        "No selecciones la fila todavía."
    ),
    keys=(
        "supervisor.result_row",
        "supervisor.select_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="supervisor_selected",
    label="Supervisor seleccionado",
    instructions=(
        "Pulsa Seleccionar. En el formulario principal, "
        "elige Tipo Interno o el valor correspondiente. "
        "Deja visible el botón Validar y no lo pulses "
        "hasta comprobar esta fase."
    ),
    keys=(
        "supervisor.selected_identifier",
        "supervisor.type_input",
        "supervisor.contract_input",
        "supervisor.validate_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="supervisor_validation_result",
    label="Supervisor validado",
    instructions=(
        "Pulsa Validar y espera hasta que aparezca "
        "Vincular y Volver. No pulses Vincular todavía."
    ),
    keys=(
        "supervisor.validation_success",
        "supervisor.link_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="supervisor_link_success",
    label="Supervisor vinculado exitosamente",
    instructions=(
        "Pulsa Vincular y espera el diálogo Éxito con "
        "el mensaje Se ha vinculado el interventor "
        "exitosamente. No pulses Aceptar todavía."
    ),
    keys=(
        "supervisor.link_success_dialog",
        "supervisor.link_success_accept",
        ),
    ),
    PortalHealthCheckPhase(
    name="availability_transition",
    label="Transición a disponibilidad presupuestal",
    instructions=(
        "Pulsa Aceptar y espera la pantalla VINCULAR "
        "DISPONIBILIDAD PRESUPUESTAL / NUEVO CONTRATO. "
        "No vincules ningún CDP todavía."
    ),
    keys=(
        "supervisor.linked",
        "availability.section",
        ),
    ),
    PortalHealthCheckPhase(
    name="availability_initial_controls",
    label="Controles de disponibilidad presupuestal",
    instructions=(
        "En la pantalla de disponibilidad, ubica el campo "
        "Buscar de la primera tabla. No vincules todavía "
        "ninguna fila."
    ),
    keys=(
        "availability.search_input",
        ),
    ),
    PortalHealthCheckPhase(
    name="availability_target_result",
    label="Disponibilidad correspondiente al CDP",
    instructions=(
        "Busca o ubica el CDP autorizado. Deja visible "
        "su fila, la celda CÓDIGO CDP y el botón Vincular. "
        "No pulses Vincular todavía."
    ),
    keys=(
        "availability.available_row",
        "availability.cdp_cell",
        "availability.link_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="availability_link_result",
    label="Disponibilidad vinculada exitosamente",
    instructions=(
        "Pulsa Vincular en la fila exacta del CDP. Cuando "
        "aparezca la notificación de éxito, presiona Enter "
        "antes de que desaparezca. La disponibilidad también "
        "debe aparecer en la tabla de vinculadas."
    ),
    keys=(
        "availability.link_success",
        "availability.linked_section",
        "availability.linked_row",
        ),
    ),
    PortalHealthCheckPhase(
    name="availability_continue",
    label="Continuar a registro presupuestal",
    instructions=(
        "Verifica que la disponibilidad permanezca en la "
        "tabla vinculada y deja visible Continuar. Presiona "
        "Enter antes de pulsarlo."
    ),
    keys=(
        "availability.continue_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="budget_register_transition",
    label="Transición a registro presupuestal",
    instructions=(
        "Pulsa Continuar y espera hasta que aparezca "
        "RETIRAR REGISTRO PRESUPUESTAL / EDITAR CONTRATO. "
        "No ingreses todavía datos presupuestales."
    ),
    keys=(
        "availability.linked",
        "budget_register.section",
        ),
    ),
    PortalHealthCheckPhase(
    name="budget_register_initial_controls",
    label="Controles del registro presupuestal",
    instructions=(
        "En la pantalla de registro presupuestal, ubica "
        "Número, Fecha, Disponibilidad Presupuestal, "
        "Total Bruto y Validar. No diligencies todavía "
        "los campos."
    ),
    keys=(
        "budget_register.number_input",
        "budget_register.date_input",
        "budget_register.availability_select",
        "budget_register.gross_total_input",
        "budget_register.validate_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="budget_register_availability_options",
    label="Disponibilidad del registro presupuestal",
    instructions=(
        "Ingresa el número y la fecha del registro. Abre "
        "Disponibilidad Presupuestal y deja visible la "
        "opción correspondiente al CDP. No la selecciones "
        "hasta comprobar esta fase."
    ),
    keys=(
        "budget_register.availability_option",
        ),
    ),
    PortalHealthCheckPhase(
    name="budget_register_validation_result",
    label="Registro presupuestal validado",
    instructions=(
        "Selecciona la disponibilidad exacta, ingresa "
        "Total Bruto y pulsa Validar. Espera a que los "
        "campos queden deshabilitados y aparezca Vincular. "
        "No pulses Vincular todavía."
    ),
    keys=(
        "budget_register.validation_success",
        "budget_register.link_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="budget_register_link_success",
    label="Registro presupuestal vinculado",
    instructions=(
        "Pulsa Vincular y espera el diálogo Éxito con el "
        "mensaje de vinculación del registro presupuestal. "
        "No pulses Aceptar todavía."
    ),
    keys=(
        "budget_register.link_success_dialog",
        "budget_register.link_success_accept",
        ),
    ),
    PortalHealthCheckPhase(
    name="additional_dates_transition",
    label="Transición a fechas adicionales",
    instructions=(
        "Pulsa Aceptar y espera hasta que aparezca "
        "VINCULAR FECHAS / NUEVO CONTRATO. No diligencies "
        "todavía las fechas."
    ),
    keys=(
        "budget_register.linked",
        "additional_dates.section",
        ),
    ),
    PortalHealthCheckPhase(
    name="additional_dates_initial_controls",
    label="Controles de fechas adicionales",
    instructions=(
        "En VINCULAR FECHAS, ubica los cuatro campos "
        "de fecha, Validar y Saltar Paso. No diligencies "
        "todavía ninguna fecha."
    ),
    keys=(
        "additional_dates.opening_date_input",
        "additional_dates.guarantee_approval_date_input",
        "additional_dates.web_publication_date_input",
        "additional_dates.secop_publication_date_input",
        "additional_dates.validate_button",
        "additional_dates.skip_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="additional_dates_calendar",
    label="Calendario de fechas adicionales",
    instructions=(
        "Abre cualquiera de los campos de fecha y deja "
        "visible el calendario con los días disponibles. "
        "No selecciones todavía una fecha."
    ),
    keys=(
        "additional_dates.calendar_dialog",
        "additional_dates.calendar_day_option",
        ),
    ),
    PortalHealthCheckPhase(
    name="additional_dates_validation_result",
    label="Fechas adicionales validadas",
    instructions=(
        "Diligencia las fechas aplicables y pulsa Validar. "
        "Espera hasta que los campos queden deshabilitados "
        "y aparezca Vincular. No pulses Vincular todavía."
    ),
    keys=(
        "additional_dates.validation_success",
        "additional_dates.link_button",
        ),
    ),
    PortalHealthCheckPhase(
    name="additional_dates_link_success",
    label="Fechas adicionales vinculadas",
    instructions=(
        "Pulsa Vincular y espera el diálogo Éxito con "
        "el mensaje de vinculación de las fechas. "
        "No pulses Aceptar todavía."
    ),
    keys=(
        "additional_dates.link_success_dialog",
        "additional_dates.link_success_accept",
        ),
    ),
    PortalHealthCheckPhase(
    name="file_reported_transition",
    label="Transición a anexos del contrato",
    instructions=(
        "Pulsa Aceptar y espera hasta que aparezca "
        "VINCULAR ANEXOS / NUEVO CONTRATO. No adjuntes "
        "todavía ningún archivo."
    ),
    keys=(
        "additional_dates.linked",
        "file_reported.section",
        ),
    ),
)