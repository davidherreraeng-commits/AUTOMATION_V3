from datetime import date
from decimal import Decimal

import pytest

from domain.enums import ContractorNature
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


def build_valid_contract() -> ContractData:
    contractor = ContractorData(
        document_number="900469775-8",
        nature=ContractorNature.LEGAL_ENTITY,
    )

    supervisor = SupervisorData(
        document_number="71693738",
        supervisor_type="Supervisor",
    )

    budget = BudgetData(
        year=2026,
        item="IDEA-2026 - RECURSOS CONVENIO IDEA",
        subsector="Tecnología",
        cdp_code="235097",
        gross_total=Decimal("1476190"),
        budget_register_number="950172",
        budget_register_date=date(2026, 2, 11),
    )

    return ContractData(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
        contractor=contractor,
        project_code="I-23021-2026",
        object_description=(
            "Servicio de software para la administración y control "
            "del sistema institucional."
        ),
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 20),
        amount=Decimal("1476190"),
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=budget,
        supervisor=supervisor,
        secop_url="https://community.secop.gov.co/example",
        guarantee_approval_date=date(2026, 1, 21),
        website_publication_date=date(2026, 1, 22),
        secop_publication_date=date(2026, 1, 22),
    )


def test_should_create_valid_contract() -> None:
    contract = build_valid_contract()

    assert contract.contract_number == "70-2026"
    assert contract.contractor.document_number == "900469775-8"
    assert contract.budget.cdp_code == "235097"
    assert contract.amount == Decimal("1476190")


def test_should_reject_empty_contract_number() -> None:
    valid_contract = build_valid_contract()

    with pytest.raises(
        ValueError,
        match="contract_number",
    ):
        ContractData(
            contract_number=" ",
            dependency=valid_contract.dependency,
            contractor=valid_contract.contractor,
            project_code=valid_contract.project_code,
            object_description=valid_contract.object_description,
            signing_date=valid_contract.signing_date,
            starting_date=valid_contract.starting_date,
            amount=valid_contract.amount,
            term_days=valid_contract.term_days,
            process_type=valid_contract.process_type,
            procedure=valid_contract.procedure,
            contract_type=valid_contract.contract_type,
            budget=valid_contract.budget,
            supervisor=valid_contract.supervisor,
        )


def test_should_reject_non_positive_amount() -> None:
    valid_contract = build_valid_contract()

    with pytest.raises(
        ValueError,
        match="mayor que cero",
    ):
        ContractData(
            contract_number=valid_contract.contract_number,
            dependency=valid_contract.dependency,
            contractor=valid_contract.contractor,
            project_code=valid_contract.project_code,
            object_description=valid_contract.object_description,
            signing_date=valid_contract.signing_date,
            starting_date=valid_contract.starting_date,
            amount=Decimal("0"),
            term_days=valid_contract.term_days,
            process_type=valid_contract.process_type,
            procedure=valid_contract.procedure,
            contract_type=valid_contract.contract_type,
            budget=valid_contract.budget,
            supervisor=valid_contract.supervisor,
        )