from __future__ import annotations

from datetime import date
from decimal import Decimal

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchContractAdditionalDatesLinkProbeResult,
)
from domain.enums.contractor_nature import ContractorNature
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


class FakeElement:
    def __init__(self, key: str) -> None:
        self.key = key


class FakeResolver:
    def __init__(self) -> None:
        self.visible_keys: list[str] = []

    def visible(self, key: str, timeout_seconds: float):
        self.visible_keys.append(key)
        return FakeElement(key)


class FakeWaits:
    pass


class FakeDriver:
    pass


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def contract(
    *,
    guarantee_date: date | None = date(2026, 8, 3),
    website_date: date | None = date(2026, 8, 3),
    secop_date: date | None = date(2026, 8, 3),
) -> ContractData:
    return ContractData(
        contract_number="90-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.NATURAL_PERSON,
            document_number="1042063697",
        ),
        project_code="I-23021-2026",
        object_description="Contrato de prueba C9.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1"),
        term_days=30,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="2111340000101501",
            subsector="Tecnología",
            cdp_code="704",
            budget_register_number="14",
            budget_register_date=date(2026, 8, 3),
            gross_total=Decimal("1"),
        ),
        supervisor=SupervisorData("52263286", "Interno"),
        secop_url="https://community.secop.gov.co/test",
        guarantee_approval_date=guarantee_date,
        website_publication_date=website_date,
        secop_publication_date=secop_date,
    )


def configure_spies(subject, monkeypatch):
    written: list[tuple[str, str]] = []
    clicked: list[tuple[str, str]] = []

    def write_date(**kwargs):
        written.append((kwargs["key"], kwargs["expected"]))

    def click_confirm(**kwargs):
        clicked.append((kwargs["click_key"], kwargs["target_key"]))
        return FakeElement(kwargs["target_key"])

    monkeypatch.setattr(
        subject,
        "_write_date_field_by_key_and_confirm",
        write_date,
    )
    monkeypatch.setattr(
        subject,
        "_click_and_confirm_visible",
        click_confirm,
    )
    return written, clicked


def test_result_normalizes_code_and_flags() -> None:
    result = BatchContractAdditionalDatesLinkProbeResult(
        success=True,
        code="contract_additional_dates_link_ready",
        message="Listo.",
        additional_dates_linked_confirmed=True,
        file_reported_section_found=True,
    )

    assert result.code == "CONTRACT_ADDITIONAL_DATES_LINK_READY"
    assert result.additional_dates_linked_confirmed is True
    assert result.file_reported_section_found is True


def test_should_write_validate_and_link_provided_dates(monkeypatch) -> None:
    subject = probe()
    resolver = FakeResolver()
    written, clicked = configure_spies(subject, monkeypatch)

    flags = subject._link_additional_dates_and_confirm(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(),
    )

    assert written == [
        (
            "additional_dates.guarantee_approval_date_input",
            "2026-08-03",
        ),
        (
            "additional_dates.web_publication_date_input",
            "2026-08-03",
        ),
        (
            "additional_dates.secop_publication_date_input",
            "2026-08-03",
        ),
    ]
    assert clicked == [
        (
            "additional_dates.validate_button",
            "additional_dates.validation_success",
        ),
        (
            "additional_dates.link_button",
            "additional_dates.link_success_dialog",
        ),
        (
            "additional_dates.link_success_accept",
            "file_reported.section",
        ),
    ]
    assert flags["additional_dates_linked_confirmed"] is True
    assert flags["file_reported_section_found"] is True


def test_opening_date_must_remain_unmodified(monkeypatch) -> None:
    subject = probe()
    written, _ = configure_spies(subject, monkeypatch)

    subject._link_additional_dates_and_confirm(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=FakeResolver(),
        contract=contract(),
    )

    assert all(
        key != "additional_dates.opening_date_input"
        for key, _ in written
    )


def test_should_skip_individual_missing_dates(monkeypatch) -> None:
    subject = probe()
    written, _ = configure_spies(subject, monkeypatch)

    flags = subject._link_additional_dates_and_confirm(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=FakeResolver(),
        contract=contract(
            guarantee_date=None,
            website_date=None,
            secop_date=date(2026, 8, 3),
        ),
    )

    assert written == [
        (
            "additional_dates.secop_publication_date_input",
            "2026-08-03",
        )
    ]
    assert flags["guarantee_approval_date_provided"] is False
    assert flags["website_publication_date_provided"] is False
    assert flags["secop_publication_date_written"] is True


def test_should_use_skip_when_no_dates_are_supplied(monkeypatch) -> None:
    subject = probe()
    written, clicked = configure_spies(subject, monkeypatch)

    flags = subject._link_additional_dates_and_confirm(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=FakeResolver(),
        contract=contract(
            guarantee_date=None,
            website_date=None,
            secop_date=None,
        ),
    )

    assert written == []
    assert clicked == [
        (
            "additional_dates.skip_button",
            "file_reported.section",
        )
    ]
    assert flags["additional_dates_skipped"] is True
    assert flags["additional_dates_linked_confirmed"] is True
    assert flags["file_reported_section_found"] is True


def test_should_reject_missing_register_number_before_browser() -> None:
    current = contract()
    object.__setattr__(
        current.budget,
        "budget_register_number",
        None,
    )

    result = probe().probe_contract_additional_dates_link(
        portal_username="usuario",
        portal_password="clave",
        contract=current,
    )

    assert result.success is False
    assert result.code == "MISSING_BUDGET_REGISTER_NUMBER"


def test_should_reject_non_positive_gross_total_before_browser() -> None:
    current = contract()
    object.__setattr__(current.budget, "gross_total", Decimal("0"))

    result = probe().probe_contract_additional_dates_link(
        portal_username="usuario",
        portal_password="clave",
        contract=current,
    )

    assert result.success is False
    assert result.code == "INVALID_GROSS_TOTAL"
