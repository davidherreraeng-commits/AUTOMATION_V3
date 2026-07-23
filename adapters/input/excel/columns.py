from __future__ import annotations


class ContractField:
    """
    Nombres canónicos internos para los datos importados.

    Estos nombres no dependen del texto exacto usado en el Excel.
    """

    CONTRACT_NUMBER = "contract_number"
    DEPENDENCY = "dependency"

    CONTRACTOR_DOCUMENT = "contractor_document"
    CONTRACTOR_NATURE = "contractor_nature"

    PROJECT_CODE = "project_code"
    OBJECT_DESCRIPTION = "object_description"

    SIGNING_DATE = "signing_date"
    STARTING_DATE = "starting_date"

    AMOUNT = "amount"
    TERM_DAYS = "term_days"

    PROCESS_TYPE = "process_type"
    PROCEDURE = "procedure"
    CONTRACT_TYPE = "contract_type"

    BUDGET_ITEM = "budget_item"
    BUDGET_SUBSECTOR = "budget_subsector"

    SECOP_URL = "secop_url"

    SUPERVISOR_DOCUMENT = "supervisor_document"
    SUPERVISOR_TYPE = "supervisor_type"

    CDP_CODE = "cdp_code"

    BUDGET_REGISTER_NUMBER = "budget_register_number"
    BUDGET_REGISTER_DATE = "budget_register_date"
    GROSS_TOTAL = "gross_total"

    GUARANTEE_APPROVAL_DATE = "guarantee_approval_date"
    WEBSITE_PUBLICATION_DATE = "website_publication_date"
    SECOP_PUBLICATION_DATE = "secop_publication_date"


COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    ContractField.CONTRACT_NUMBER: (
        "No. de Contrato",
        "Número de Contrato",
        "Numero de Contrato",
        "No Contrato",
    ),
    ContractField.DEPENDENCY: (
        "Dependencia",
        "Nombre Dependencia",
    ),
    ContractField.CONTRACTOR_DOCUMENT: (
        "Cédula o Nit de Contratista",
        "Cédula o Nit Contratista",
        "Cedula o Nit de Contratista",
        "Cedula o Nit Contratista",
        "Identificación Contratista",
        "Identificacion Contratista",
    ),
    ContractField.CONTRACTOR_NATURE: (
        "Tipo Persona",
        "Tipo de Persona",
        "Naturaleza Contratista",
        "Naturaleza del Contratista",
    ),
    ContractField.PROJECT_CODE: (
        "Código del Proyecto",
        "Codigo del Proyecto",
        "Código Proyecto",
        "Codigo Proyecto",
    ),
    ContractField.OBJECT_DESCRIPTION: (
        "Objeto del Contrato",
        "Objeto Contrato",
    ),
    ContractField.SIGNING_DATE: (
        "Fecha de Suscripción",
        "Fecha de Suscripcion",
        "Fecha Suscripción",
        "Fecha Suscripcion",
    ),
    ContractField.STARTING_DATE: (
        "Fecha de Inicio",
        "Fecha Inicio",
    ),
    ContractField.AMOUNT: (
        "Valor",
        "Valor del Contrato",
        "Valor Contrato",
    ),
    ContractField.TERM_DAYS: (
        "Plazo Estimado (En Dias)",
        "Plazo Estimado (En Días)",
        "Plazo Estimado",
        "Plazo en Días",
        "Plazo en Dias",
    ),
    ContractField.PROCESS_TYPE: (
        "Modalidad o Proceso",
        "Modalidad",
        "Proceso",
    ),
    ContractField.PROCEDURE: (
        "Procedimiento/Causal",
        "Procedimiento / Causal",
        "Procedimiento",
        "Causal",
    ),
    ContractField.CONTRACT_TYPE: (
        "Tipo de Contrato",
        "Tipo Contrato",
    ),
    ContractField.BUDGET_ITEM: (
        "Rubro Presupuestal",
        "Rubro",
    ),
    ContractField.BUDGET_SUBSECTOR: (
        "Sub-Sector",
        "Sub Sector",
        "Subsector",
    ),
    ContractField.SECOP_URL: (
        "Enlace Proceso SECOP II",
        "URL SECOP",
        "Enlace SECOP",
        "URL del Contrato en el SECOP",
    ),
    ContractField.SUPERVISOR_DOCUMENT: (
        "Cédula Supervisor",
        "Cedula Supervisor",
        "Identificación Supervisor",
        "Identificacion Supervisor",
        "Cédula Interventor",
        "Cedula Interventor",
    ),
    ContractField.SUPERVISOR_TYPE: (
        "Tipo Interventor",
        "Tipo Supervisor",
        "Tipo de Interventor",
        "Tipo de Supervisor",
    ),
    ContractField.CDP_CODE: (
        "No. CDP",
        "No CDP",
        "Código CDP",
        "Codigo CDP",
        "CDP",
    ),
    ContractField.BUDGET_REGISTER_NUMBER: (
        "No. RP",
        "No RP",
        "No. Registro Presupuestal",
        "Número Registro Presupuestal",
        "Numero Registro Presupuestal",
    ),
    ContractField.BUDGET_REGISTER_DATE: (
        "Fecha RP",
        "Fecha Registro Presupuestal",
    ),
    ContractField.GROSS_TOTAL: (
        "Total Bruto",
        "Valor Total Bruto",
    ),
    ContractField.GUARANTEE_APPROVAL_DATE: (
        "Fecha Aprobación Garantía Única",
        "Fecha Aprobacion Garantia Unica",
    ),
    ContractField.WEBSITE_PUBLICATION_DATE: (
        "Fecha Publicación pagina Web",
        "Fecha Publicación Página Web",
        "Fecha Publicacion Pagina Web",
    ),
    ContractField.SECOP_PUBLICATION_DATE: (
        "Fecha Publicación SECOP II",
        "Fecha Publicacion SECOP II",
        "Publicación Secop",
        "Publicacion Secop",
    ),
}


REQUIRED_CONTRACT_FIELDS: tuple[str, ...] = (
    ContractField.CONTRACT_NUMBER,
    ContractField.CONTRACTOR_DOCUMENT,
    ContractField.CONTRACTOR_NATURE,
    ContractField.PROJECT_CODE,
    ContractField.OBJECT_DESCRIPTION,
    ContractField.SIGNING_DATE,
    ContractField.STARTING_DATE,
    ContractField.AMOUNT,
    ContractField.TERM_DAYS,
    ContractField.PROCESS_TYPE,
    ContractField.PROCEDURE,
    ContractField.CONTRACT_TYPE,
    ContractField.BUDGET_ITEM,
    ContractField.BUDGET_SUBSECTOR,
    ContractField.SUPERVISOR_DOCUMENT,
    ContractField.CDP_CODE,
)