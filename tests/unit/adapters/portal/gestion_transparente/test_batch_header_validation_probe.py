from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchHeaderValidationProbeResult,
)
from domain.enums.contractor_nature import ContractorNature
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


@dataclass
class FakeElement:
    value: str = ""
    text: str = ""

    def clear(self) -> None:
        self.value = ""

    def send_keys(self, *values) -> None:
        for value in values:
            text = str(value)
            if len(text) == 1 and ord(text) >= 0xE000:
                continue
            self.value += text

    def get_attribute(self, name: str):
        if name == "value":
            return self.value
        return None


class FakeResolver:
    def __init__(self, *, missing: set[str] | None = None) -> None:
        self.missing = missing or set()
        self.contract_number = FakeElement()
        self.validate = FakeElement()

    def optional_visible(self, key: str, *, timeout_seconds: float):
        if key in self.missing:
            return None
        return FakeElement(text=key)

    def visible(self, key: str, *, timeout_seconds: float):
        if key == "contract.header.contract_number":
            return self.contract_number
        return FakeElement(text=key)

    def clickable(self, key: str, *, timeout_seconds: float):
        if key == "contract.header.validate_button":
            return self.validate
        return FakeElement(text=key)


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def contract() -> ContractData:
    return ContractData(
        contract_number="80-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.LEGAL_ENTITY,
            document_number="901398448-2",
        ),
        project_code="I-23021-2026",
        object_description="Servicio institucional.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1476190"),
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="IDEA-2026",
            subsector="Tecnología",
            cdp_code="235097",
            budget_register_number="950172",
            gross_total=Decimal("1476190"),
        ),
        supervisor=SupervisorData("71693738", "Interno"),
        secop_url="https://community.secop.gov.co/example",
    )


def test_validation_result_never_reports_save_by_default() -> None:
    outcome = BatchHeaderValidationProbeResult(
        success=True,
        code="header_validation_ready",
        message="C3 disponible.",
        validate_clicked=True,
        header_validation_confirmed=True,
        general_data_ready=True,
    )

    assert outcome.code == "HEADER_VALIDATION_READY"
    assert outcome.validate_clicked is True
    assert outcome.save_clicked is False


def test_should_confirm_all_general_core_controls() -> None:
    flags, missing = probe()._inspect_general_core_controls(
        FakeResolver()
    )

    assert all(flags.values())
    assert missing == ()


def test_should_report_missing_general_core_controls() -> None:
    flags, missing = probe()._inspect_general_core_controls(
        FakeResolver(
            missing={
                "general.starting_date",
                "general.contract_term",
            }
        )
    )

    assert flags["general_starting_date_found"] is False
    assert flags["general_contract_term_found"] is False
    assert missing == ("Fecha de inicio", "Plazo estimado")


def test_shared_header_population_prepares_validate_without_clicking_it() -> None:
    subject = probe()
    resolver = FakeResolver()
    calls: list[str] = []

    subject._select_contract_record_type = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append("record-type")
    )
    subject._select_contractor_draft = (  # type: ignore[method-assign]
        lambda **kwargs: {
            "contractor_dialog_opened": True,
            "contractor_nature_selected": True,
            "contractor_document_written": True,
            "contractor_result_found": True,
            "contractor_selected": True,
        }
    )
    subject._select_project_draft = (  # type: ignore[method-assign]
        lambda **kwargs: {
            "project_dialog_opened": True,
            "project_code_written": True,
            "project_result_found": True,
            "project_selected": True,
        }
    )

    flags = subject._populate_header_draft(
        driver=object(),
        waits=object(),
        resolver=resolver,
        contract=contract(),
    )

    assert calls == ["record-type"]
    assert resolver.contract_number.value == "80-2026"
    assert flags["contractor_selected"] is True
    assert flags["project_selected"] is True
    assert flags["validate_button_found"] is True
