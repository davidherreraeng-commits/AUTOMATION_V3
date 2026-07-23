from datetime import date
from decimal import Decimal

from adapters.input.excel import (
    ContractField,
    ContractRowMapper,
)
from domain.enums import ContractorNature


def build_valid_canonical_row() -> dict:
    return {
        ContractField.CONTRACT_NUMBER: "70-2026",
        ContractField.DEPENDENCY: None,
        ContractField.CONTRACTOR_DOCUMENT: "900469775-8",
        ContractField.CONTRACTOR_NATURE: "Jurídica",
        ContractField.PROJECT_CODE: "I-23021-2026",
        ContractField.OBJECT_DESCRIPTION: (
            "Servicio de software para la administración "
            "del sistema institucional."
        ),
        ContractField.SIGNING_DATE: "20/01/2026",
        ContractField.STARTING_DATE: "21/01/2026",
        ContractField.AMOUNT: "$ 1.476.190",
        ContractField.TERM_DAYS: 180.0,
        ContractField.PROCESS_TYPE: "Contratación Directa",
        ContractField.PROCEDURE: "Prestación de Servicios",
        ContractField.CONTRACT_TYPE: "Servicios",
        ContractField.BUDGET_ITEM: (
            "IDEA-2026 - RECURSOS CONVENIO IDEA"
        ),
        ContractField.BUDGET_SUBSECTOR: "Tecnología",
        ContractField.SECOP_URL: (
            "https://community.secop.gov.co/example"
        ),
        ContractField.SUPERVISOR_DOCUMENT: 71693738.0,
        ContractField.SUPERVISOR_TYPE: "Supervisor",
        ContractField.CDP_CODE: 235097.0,
        ContractField.BUDGET_REGISTER_NUMBER: 950172.0,
        ContractField.BUDGET_REGISTER_DATE: "11/02/2026",
        ContractField.GROSS_TOTAL: "$ 1.476.190",
        ContractField.GUARANTEE_APPROVAL_DATE: "22/01/2026",
        ContractField.WEBSITE_PUBLICATION_DATE: "23/01/2026",
        ContractField.SECOP_PUBLICATION_DATE: "23/01/2026",
    }


def create_mapper() -> ContractRowMapper:
    return ContractRowMapper(
        default_dependency="Proyectos Especiales",
        default_budget_year=2026,
    )


def test_should_map_valid_legal_entity_contract() -> None:
    result = create_mapper().map(
        row_number=2,
        canonical_row=build_valid_canonical_row(),
    )

    assert result.is_valid
    assert result.issues == ()
    assert result.contract is not None

    contract = result.contract

    assert contract.contract_number == "70-2026"
    assert contract.dependency == "Proyectos Especiales"
    assert (
        contract.contractor.nature
        is ContractorNature.LEGAL_ENTITY
    )
    assert (
        contract.contractor.document_number
        == "900469775-8"
    )
    assert (
        contract.supervisor.document_number
        == "71693738"
    )
    assert contract.budget.cdp_code == "235097"
    assert (
        contract.budget.budget_register_number
        == "950172"
    )
    assert contract.amount == Decimal("1476190")
    assert contract.signing_date == date(2026, 1, 20)


def test_should_map_natural_person() -> None:
    row = build_valid_canonical_row()
    row[ContractField.CONTRACTOR_NATURE] = (
        "Persona Natural"
    )
    row[ContractField.CONTRACTOR_DOCUMENT] = (
        1001360022.0
    )

    result = create_mapper().map(
        row_number=2,
        canonical_row=row,
    )

    assert result.is_valid
    assert result.contract is not None
    assert (
        result.contract.contractor.nature
        is ContractorNature.NATURAL_PERSON
    )
    assert (
        result.contract.contractor.document_number
        == "1001360022"
    )


def test_should_collect_multiple_row_issues() -> None:
    row = build_valid_canonical_row()
    row[ContractField.CONTRACT_NUMBER] = None
    row[ContractField.CONTRACTOR_NATURE] = "Colectiva"
    row[ContractField.AMOUNT] = "valor inválido"

    result = create_mapper().map(
        row_number=4,
        canonical_row=row,
    )

    assert result.is_invalid
    assert result.contract is None
    assert len(result.issues) == 3

    issue_codes = {
        issue.code
        for issue in result.issues
    }

    assert "INVALID_VALUE" in issue_codes
    assert (
        "UNSUPPORTED_CONTRACTOR_NATURE"
        in issue_codes
    )


def test_should_use_amount_when_gross_total_is_missing() -> None:
    row = build_valid_canonical_row()
    row[ContractField.GROSS_TOTAL] = None

    result = create_mapper().map(
        row_number=2,
        canonical_row=row,
    )

    assert result.is_valid
    assert result.contract is not None
    assert (
        result.contract.budget.gross_total
        == result.contract.amount
    )


def test_should_accept_missing_optional_fields() -> None:
    row = build_valid_canonical_row()

    row[ContractField.SECOP_URL] = None
    row[ContractField.SUPERVISOR_TYPE] = None
    row[ContractField.BUDGET_REGISTER_NUMBER] = None
    row[ContractField.BUDGET_REGISTER_DATE] = None
    row[ContractField.GUARANTEE_APPROVAL_DATE] = None
    row[ContractField.WEBSITE_PUBLICATION_DATE] = None
    row[ContractField.SECOP_PUBLICATION_DATE] = None

    result = create_mapper().map(
        row_number=2,
        canonical_row=row,
    )

    assert result.is_valid
    assert result.contract is not None
    assert result.contract.secop_url is None
    assert (
        result.contract.supervisor.supervisor_type
        is None
    )
    assert (
        result.contract.budget.budget_register_number
        is None
    )