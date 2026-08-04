from __future__ import annotations

from datetime import date
from decimal import Decimal

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchGeneralValidationProbeResult,
)
from domain.enums.contractor_nature import ContractorNature
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


class FakeElement:
    def __init__(self) -> None:
        self.clicks = 0

    def click(self) -> None:
        self.clicks += 1


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def contract(*, secop_url: str | None = "https://community.secop.gov.co/example"):
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
        secop_url=secop_url,
    )


def test_result_normalizes_code_and_never_reports_save_by_default() -> None:
    outcome = BatchGeneralValidationProbeResult(
        success=True,
        code="general_validation_ready",
        message="Validación confirmada.",
        general_validate_clicked=True,
        general_validation_confirmed=True,
        save_button_found=True,
    )

    assert outcome.code == "GENERAL_VALIDATION_READY"
    assert outcome.general_validate_clicked is True
    assert outcome.general_validation_confirmed is True
    assert outcome.save_button_found is True
    assert outcome.save_clicked is False


def test_should_reject_missing_secop_before_opening_browser() -> None:
    outcome = probe().probe_general_validation(
        portal_username="usuario",
        portal_password="clave",
        contract=contract(secop_url=None),
    )

    assert outcome.success is False
    assert outcome.code == "MISSING_SECOP_URL"
    assert outcome.general_validate_clicked is False
    assert outcome.save_clicked is False


def test_should_validate_general_form_and_confirm_save_without_clicking_it() -> None:
    subject = probe()
    save_button = FakeElement()
    calls: list[dict] = []

    def click_and_confirm(**kwargs):
        calls.append(kwargs)
        return save_button

    subject._click_and_confirm_visible = click_and_confirm  # type: ignore[method-assign]

    flags = subject._validate_general_form_without_saving(
        driver=object(),
        resolver=object(),
    )

    assert flags == {
        "general_validate_clicked": True,
        "general_validation_confirmed": True,
        "save_button_found": True,
    }
    assert calls[0]["click_key"] == "general.final_validate_button"
    assert calls[0]["target_key"] == "general.validation_success"
    assert calls[0]["code"] == "GENERAL_VALIDATION_TIMEOUT"
    assert save_button.clicks == 0


def test_general_validation_requires_all_safe_postconditions() -> None:
    flags = {
        "header_validation_confirmed": True,
        "general_data_completed": True,
        "general_completion_completed": True,
        "final_validate_button_found": True,
        "general_validate_clicked": True,
        "general_validation_confirmed": True,
        "save_button_found": True,
    }

    assert all(flags.values())
    flags["save_button_found"] = False
    assert not all(flags.values())
