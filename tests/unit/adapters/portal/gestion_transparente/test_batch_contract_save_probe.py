from __future__ import annotations

from datetime import date
from decimal import Decimal

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchContractSaveProbeResult,
)
from domain.enums.contractor_nature import ContractorNature
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


class FakeElement:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.text = ""
        self.clicks = 0

    def click(self) -> None:
        self.clicks += 1

    def get_attribute(self, name: str):
        if name == "value":
            return self.value
        return None


class FakeResolver:
    def __init__(self) -> None:
        self.accept = FakeElement()
        self.saved = FakeElement("80-2026")
        self.supervisor = FakeElement()

    def clickable(self, key: str, **kwargs):
        assert key == "general.save_success_accept"
        return self.accept

    def optional_visible(self, key: str, **kwargs):
        if key == "general.contract_saved":
            return self.saved
        if key == "supervisor.section":
            return self.supervisor
        raise AssertionError(key)


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def contract(*, secop_url: str | None = "https://community.secop.gov.co/test"):
    return ContractData(
        contract_number="80-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.LEGAL_ENTITY,
            document_number="901398448-2",
        ),
        project_code="I-23021-2026",
        object_description="Contrato de prueba.",
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
            cdp_code="235097",
            budget_register_number="950172",
            gross_total=Decimal("1"),
        ),
        supervisor=SupervisorData("71693738", "Interno"),
        secop_url=secop_url,
    )


def test_result_normalizes_code_and_save_flags() -> None:
    outcome = BatchContractSaveProbeResult(
        success=True,
        code="contract_save_ready",
        message="Guardado.",
        save_clicked=True,
        success_dialog_found=True,
        success_dialog_accepted=True,
        contract_saved_confirmed=True,
        supervisor_section_found=True,
    )

    assert outcome.code == "CONTRACT_SAVE_READY"
    assert outcome.save_clicked is True
    assert outcome.success_dialog_found is True
    assert outcome.success_dialog_accepted is True
    assert outcome.contract_saved_confirmed is True
    assert outcome.supervisor_section_found is True


def test_should_reject_missing_secop_before_opening_browser() -> None:
    outcome = probe().probe_contract_save(
        portal_username="usuario",
        portal_password="clave",
        contract=contract(secop_url=None),
    )

    assert outcome.success is False
    assert outcome.code == "MISSING_SECOP_URL"
    assert outcome.save_clicked is False


def test_should_click_save_accept_dialog_and_confirm_supervisor() -> None:
    subject = probe()
    resolver = FakeResolver()
    save_calls: list[dict] = []

    subject._click_and_confirm_visible = (  # type: ignore[method-assign]
        lambda **kwargs: save_calls.append(kwargs) or FakeElement()
    )
    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._perform_click = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].click()
    )

    flags = subject._save_contract_and_confirm(
        driver=object(),
        resolver=resolver,
        contract=contract(),
    )

    assert save_calls[0]["click_key"] == "general.save_button"
    assert save_calls[0]["target_key"] == "general.save_success_dialog"
    assert flags == {
        "save_clicked": True,
        "success_dialog_found": True,
        "success_dialog_accepted": True,
        "contract_saved_confirmed": True,
        "supervisor_section_found": True,
    }
    assert resolver.accept.clicks == 1


def test_contract_save_requires_every_postcondition() -> None:
    flags = {
        "header_validation_confirmed": True,
        "general_data_completed": True,
        "general_completion_completed": True,
        "general_validation_confirmed": True,
        "save_button_found": True,
        "save_clicked": True,
        "success_dialog_found": True,
        "success_dialog_accepted": True,
        "contract_saved_confirmed": True,
        "supervisor_section_found": True,
    }
    assert all(flags.values())
    flags["supervisor_section_found"] = False
    assert not all(flags.values())
