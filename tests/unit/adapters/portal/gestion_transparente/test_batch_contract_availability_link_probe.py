from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchContractAvailabilityLinkProbeResult,
)
from domain.enums.contractor_nature import ContractorNature
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


class Cell:
    text = ""
    def __init__(self, value: str) -> None:
        self.value = value
    def get_attribute(self, name: str):
        return self.value if name == "title" else None


class Row:
    def __init__(self, cdp: str) -> None:
        self.cdp = cdp
    def find_element(self, by, value):
        return Cell(self.cdp)


class Driver:
    def __init__(self, rows):
        self.rows = rows
    def find_elements(self, by, value):
        return self.rows


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def contract(cdp: str = "700") -> ContractData:
    return ContractData(
        contract_number="86-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.NATURAL_PERSON,
            document_number="1042063697",
        ),
        project_code="I-23021-2026",
        object_description="Contrato de prueba CDP.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1"),
        term_days=30,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="IDEA-2026",
            subsector="Tecnología",
            cdp_code=cdp,
            budget_register_number="10",
            gross_total=Decimal("1"),
        ),
        supervisor=SupervisorData("71693738", "Interno"),
        secop_url="https://community.secop.gov.co/test",
    )


def test_result_normalizes_code_and_flags() -> None:
    result = BatchContractAvailabilityLinkProbeResult(
        success=True,
        code="contract_availability_link_ready",
        message="Listo.",
        contract_saved_confirmed=True,
        supervisor_linked_confirmed=True,
        availability_linked_row_confirmed=True,
        budget_register_section_found=True,
    )
    assert result.code == "CONTRACT_AVAILABILITY_LINK_READY"
    assert result.contract_saved_confirmed is True
    assert result.supervisor_linked_confirmed is True
    assert result.availability_linked_row_confirmed is True
    assert result.budget_register_section_found is True


def test_should_reject_missing_cdp_before_browser() -> None:
    current = contract()
    object.__setattr__(current.budget, "cdp_code", "")
    result = probe().probe_contract_availability_link(
        portal_username="usuario",
        portal_password="clave",
        contract=current,
    )
    assert result.success is False
    assert result.code == "MISSING_CDP_CODE"


@pytest.mark.parametrize(
    ("expected", "observed"),
    [("700", "700"), ("235097", "235097(950172)")],
)
def test_cdp_matching_accepts_exact_and_decorated(
    expected: str, observed: str,
) -> None:
    assert probe()._cdp_matches(expected=expected, observed=observed)


def test_cdp_matching_rejects_partial_suffix() -> None:
    assert not probe()._cdp_matches(expected="700", observed="237700")


def test_should_find_exact_availability_row() -> None:
    target = Row("700")
    found = probe()._find_availability_row(
        driver=Driver([Row("237700(950183)"), target]),
        expected_cdp="700",
        linked=False,
    )
    assert found is target


def test_should_return_false_when_cdp_is_absent() -> None:
    found = probe()._find_availability_row(
        driver=Driver([Row("237700(950183)")]),
        expected_cdp="700",
        linked=False,
    )
    assert found is False
