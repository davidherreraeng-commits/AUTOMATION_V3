from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from application.services.contract_value_policy import ContractValuePolicy
from domain.enums.contractor_nature import ContractorNature
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


def contract(
    number: str = "70-2026",
    *,
    amount: Decimal = Decimal("1"),
    gross_total: Decimal = Decimal("1"),
) -> ContractData:
    return ContractData(
        contract_number=number,
        dependency="Adquisiciones",
        contractor=ContractorData(
            document_number="900469775-8",
            nature=ContractorNature.LEGAL_ENTITY,
        ),
        project_code="I-23021-2026",
        object_description="Servicio institucional.",
        signing_date=date(2026, 8, 4),
        starting_date=date(2026, 8, 4),
        amount=amount,
        term_days=365,
        process_type="Contratación Directa",
        procedure="Sin Pluralidad De Oferentes",
        contract_type="Contrato de Prestación de Servicios",
        budget=BudgetData(
            year=2026,
            item="IDEA-2026 - RECURSOS CONVENIO IDEA",
            subsector="Tecnología",
            cdp_code="700",
            gross_total=gross_total,
            budget_register_number="10",
        ),
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Interno",
        ),
        secop_url="https://community.secop.gov.co/example",
    )


def test_should_block_nominal_value_without_explicit_allowlist() -> None:
    assessment = ContractValuePolicy().assess(contract())

    assert assessment is not None
    assert assessment.code == "TEST_VALUES_DETECTED"
    assert assessment.blocking is True


def test_should_allow_exact_institutional_nominal_contract() -> None:
    policy = ContractValuePolicy(
        allowed_contract_numbers=(" 70-2026 ",),
    )

    assessment = policy.assess(contract(number="70-2026"))

    assert assessment is not None
    assert assessment.code == "NOMINAL_VALUE_INSTITUTIONALLY_ALLOWED"
    assert assessment.blocking is False


def test_should_normalize_case_and_repeated_spaces() -> None:
    policy = ContractValuePolicy(
        allowed_contract_numbers=(" contrato   especial ",),
    )

    assessment = policy.assess(
        contract(number="CONTRATO ESPECIAL"),
    )

    assert assessment is not None
    assert assessment.blocking is False


def test_should_not_accept_partial_contract_number_match() -> None:
    policy = ContractValuePolicy(
        allowed_contract_numbers=("70-202",),
    )

    assessment = policy.assess(contract(number="70-2026"))

    assert assessment is not None
    assert assessment.code == "TEST_VALUES_DETECTED"
    assert assessment.blocking is True


def test_should_reject_wildcard_allowlist() -> None:
    with pytest.raises(ValueError, match="no admite"):
        ContractValuePolicy(allowed_contract_numbers=("*",))


def test_should_not_emit_issue_for_non_nominal_values() -> None:
    policy = ContractValuePolicy(
        allowed_contract_numbers=("70-2026",),
    )

    assert policy.assess(
        contract(
            amount=Decimal("2"),
            gross_total=Decimal("2"),
        )
    ) is None
