from __future__ import annotations

from datetime import date
from decimal import Decimal

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchContractBudgetRegisterLinkProbeResult,
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
        self.clickable_keys: list[str] = []

    def visible(self, key: str, timeout_seconds: float):
        self.visible_keys.append(key)
        return FakeElement(key)

    def clickable(self, key: str, timeout_seconds: float):
        self.clickable_keys.append(key)
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
    register_number: str | None = "25",
    register_date: date | None = date(2026, 8, 3),
    gross_total: Decimal = Decimal("125.50"),
    amount: Decimal = Decimal("999"),
) -> ContractData:
    return ContractData(
        contract_number="87-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.NATURAL_PERSON,
            document_number="1042063697",
        ),
        project_code="I-23021-2026",
        object_description="Contrato de prueba RP.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=amount,
        term_days=30,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="2111340000101501",
            subsector="Tecnología",
            cdp_code="704",
            budget_register_number=register_number,
            budget_register_date=register_date,
            gross_total=gross_total,
        ),
        supervisor=SupervisorData("52263286", "Interno"),
        secop_url="https://community.secop.gov.co/test",
    )


def configure_helper_spies(subject, monkeypatch):
    written: list[tuple[str, object]] = []
    selected: list[dict[str, object]] = []
    clicked: list[tuple[str, str]] = []

    monkeypatch.setattr(subject, "_scroll_into_view", lambda *args, **kwargs: None)

    def write_text(**kwargs):
        written.append((kwargs["element"].key, kwargs["expected"]))

    def write_currency(**kwargs):
        written.append((kwargs["element"].key, kwargs["expected"]))

    def select_catalog(**kwargs):
        selected.append(kwargs)

    def click_confirm(**kwargs):
        clicked.append((kwargs["click_key"], kwargs["target_key"]))
        return FakeElement(kwargs["target_key"])

    def write_text_by_key(**kwargs):
        written.append((kwargs["key"], kwargs["expected"]))

    def write_currency_by_key(**kwargs):
        written.append((kwargs["key"], kwargs["expected"]))

    def write_date(**kwargs):
        written.append((kwargs["key"], kwargs["expected"]))

    # Compatibilidad con los helpers anteriores.
    monkeypatch.setattr(subject, "_write_and_confirm_wait", write_text)
    monkeypatch.setattr(subject, "_write_currency_and_confirm", write_currency)

    # Helpers productivos introducidos por el hotfix de referencias obsoletas.
    monkeypatch.setattr(
        subject,
        "_write_text_field_by_key_and_confirm",
        write_text_by_key,
    )
    monkeypatch.setattr(
        subject,
        "_write_currency_field_by_key_and_confirm",
        write_currency_by_key,
    )
    monkeypatch.setattr(
        subject,
        "_write_date_field_by_key_and_confirm",
        write_date,
    )
    monkeypatch.setattr(subject, "_select_autocomplete_and_confirm", select_catalog)
    monkeypatch.setattr(subject, "_click_and_confirm_visible", click_confirm)
    return written, selected, clicked


def test_result_normalizes_code_and_flags() -> None:
    result = BatchContractBudgetRegisterLinkProbeResult(
        success=True,
        code="contract_budget_register_link_ready",
        message="Listo.",
        contract_saved_confirmed=True,
        supervisor_linked_confirmed=True,
        availability_linked_row_confirmed=True,
        budget_register_linked_confirmed=True,
        additional_dates_section_found=True,
    )

    assert result.code == "CONTRACT_BUDGET_REGISTER_LINK_READY"
    assert result.contract_saved_confirmed is True
    assert result.budget_register_linked_confirmed is True
    assert result.additional_dates_section_found is True


def test_should_reject_missing_register_number_before_browser() -> None:
    result = probe().probe_contract_budget_register_link(
        portal_username="usuario",
        portal_password="clave",
        contract=contract(register_number=None),
    )

    assert result.success is False
    assert result.code == "MISSING_BUDGET_REGISTER_NUMBER"


def test_should_reject_non_positive_gross_total_before_browser() -> None:
    result = probe().probe_contract_budget_register_link(
        portal_username="usuario",
        portal_password="clave",
        contract=contract(gross_total=Decimal("0")),
    )

    assert result.success is False
    assert result.code == "INVALID_GROSS_TOTAL"


def test_should_fill_validate_and_link_budget_register(
    monkeypatch,
) -> None:
    subject = probe()
    resolver = FakeResolver()
    written, selected, clicked = configure_helper_spies(subject, monkeypatch)

    flags = subject._link_budget_register_and_confirm(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(),
    )

    assert ("budget_register.number_input", "25") in written
    assert (
        "budget_register.date_input",
        "2026-08-03",
    ) in written
    assert (
        "budget_register.gross_total_input",
        Decimal("125.50"),
    ) in written
    assert selected[0]["key"] == "budget_register.availability_select"
    assert selected[0]["expected"] == "704"
    assert selected[0]["allow_decorated_value"] is True
    assert clicked == [
        (
            "budget_register.validate_button",
            "budget_register.validation_success",
        ),
        (
            "budget_register.link_button",
            "budget_register.link_success_dialog",
        ),
        (
            "budget_register.link_success_accept",
            "budget_register.linked",
        ),
    ]
    assert flags["budget_register_linked_confirmed"] is True
    assert flags["additional_dates_section_found"] is True


def test_optional_register_date_should_be_skipped(monkeypatch) -> None:
    subject = probe()
    resolver = FakeResolver()
    written, _, _ = configure_helper_spies(subject, monkeypatch)

    flags = subject._link_budget_register_and_confirm(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(register_date=None),
    )

    assert "budget_register.date_input" not in resolver.clickable_keys
    assert all(key != "budget_register.date_input" for key, _ in written)
    assert flags["budget_register_date_provided"] is False
    assert flags["budget_register_date_written"] is False
    assert flags["budget_register_linked_confirmed"] is True


def test_gross_total_must_not_use_contract_amount(monkeypatch) -> None:
    subject = probe()
    resolver = FakeResolver()
    written, _, _ = configure_helper_spies(subject, monkeypatch)

    subject._link_budget_register_and_confirm(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(
            amount=Decimal("999999"),
            gross_total=Decimal("321.45"),
        ),
    )

    assert (
        "budget_register.gross_total_input",
        Decimal("321.45"),
    ) in written
    assert (
        "budget_register.gross_total_input",
        Decimal("999999"),
    ) not in written


def test_availability_selector_uses_cdp_semantics(monkeypatch) -> None:
    subject = probe()
    resolver = FakeResolver()
    _, selected, _ = configure_helper_spies(subject, monkeypatch)

    subject._link_budget_register_and_confirm(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(),
    )

    selection = selected[0]
    assert selection["expected"] == "704"
    assert selection["label"] == "Disponibilidad Presupuestal"
    assert selection["alternative_clickable_key"] is None
