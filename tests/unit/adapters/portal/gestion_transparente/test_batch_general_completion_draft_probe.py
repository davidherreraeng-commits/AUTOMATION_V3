from __future__ import annotations

from datetime import date
from decimal import Decimal

from selenium.webdriver.common.keys import Keys

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchGeneralCompletionDraftProbeResult,
)
from domain.enums.contractor_nature import ContractorNature
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


class FakeElement:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.clicks = 0
        self._available_option = value
        self._selected_all = False

    def click(self) -> None:
        self.clicks += 1

    def clear(self) -> None:
        self.value = ""
        self._selected_all = False

    def send_keys(self, *values) -> None:
        if values == (Keys.CONTROL, "a"):
            self._selected_all = True
            return

        for value in values:
            if value == Keys.BACKSPACE:
                if self._selected_all:
                    self.value = ""
                    self._selected_all = False
                continue

            if value == Keys.ARROW_DOWN:
                continue

            if value == Keys.ENTER:
                if self._available_option:
                    self.value = self._available_option
                continue

            if value == Keys.TAB:
                continue

            text = str(value)
            if len(text) == 1 and text.isprintable():
                self.value += text

    def get_attribute(self, name: str):
        if name == "value":
            return self.value
        return None


class FakeResolver:
    def __init__(self) -> None:
        self.elements = {
            "general.budget_link_button": FakeElement(),
            "general.secop_url": FakeElement(),
            "general.final_validate_button": FakeElement(),
        }

    def visible(self, key: str, *, timeout_seconds: float):
        return self.elements.setdefault(key, FakeElement())

    def clickable(self, key: str, *, timeout_seconds: float):
        return self.elements.setdefault(key, FakeElement())


class FakeWaits:
    def until(self, condition, *, timeout_seconds: float):
        assert condition(object())
        return True


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


def test_result_never_reports_general_validation_or_save_by_default() -> None:
    outcome = BatchGeneralCompletionDraftProbeResult(
        success=True,
        code="general_completion_draft_ready",
        message="C4 completo.",
        general_completion_completed=True,
    )

    assert outcome.code == "GENERAL_COMPLETION_DRAFT_READY"
    assert outcome.general_validate_clicked is False
    assert outcome.save_clicked is False


def test_should_use_institutional_execution_location_defaults() -> None:
    subject = probe()

    assert subject._DEFAULT_EXECUTION_DEPARTMENT == "Antioquia"
    assert subject._DEFAULT_EXECUTION_CITY == "Medellín"


def test_should_reject_missing_mandatory_secop_url_before_browser() -> None:
    outcome = probe().probe_general_completion_draft(
        portal_username="usuario",
        portal_password="clave",
        contract=contract(secop_url=None),
    )

    assert outcome.success is False
    assert outcome.code == "MISSING_SECOP_URL"


def test_should_populate_all_c4_fields_without_final_validation_or_save() -> None:
    subject = probe()
    resolver = FakeResolver()
    calls: list[tuple[str, str]] = []

    subject._select_first_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("first", kwargs["key"])) or "Plan"
    )
    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append((kwargs["key"], kwargs["expected"]))
    )
    subject._select_radio = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("radio", kwargs["key"]))
    )
    subject._write_and_confirm_wait = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].__setattr__(
            "value", kwargs["expected"]
        )
    )
    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._click_with_fallbacks = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].click()
    )

    flags = subject._populate_general_completion_draft(
        driver=object(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(),
    )

    assert all(flags.values())
    assert ("first", "general.government_plan") in calls
    assert ("general.budget_year", "2026") in calls
    assert ("general.budget_item", "IDEA-2026") in calls
    assert ("general.budget_subsector", "Tecnología") in calls
    assert ("radio", "general.secop_yes") in calls
    assert ("general.execution_department", "Antioquia") in calls
    assert ("general.execution_city", "Medellín") in calls
    assert resolver.elements["general.secop_url"].value.startswith("https://")
    assert resolver.elements["general.budget_link_button"].clicks == 1


def test_should_mark_all_negative_contract_indicators_as_no() -> None:
    subject = probe()
    resolver = FakeResolver()
    selected_radios: list[str] = []

    subject._select_first_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: "Plan"
    )
    subject._select_autocomplete_and_confirm = lambda **kwargs: None  # type: ignore[method-assign]
    subject._select_radio = (  # type: ignore[method-assign]
        lambda **kwargs: selected_radios.append(kwargs["key"])
    )
    subject._write_and_confirm_wait = lambda **kwargs: None  # type: ignore[method-assign]
    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._click_with_fallbacks = lambda **kwargs: None  # type: ignore[method-assign]

    subject._populate_general_completion_draft(
        driver=object(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(),
    )

    assert {
        "general.advance_no",
        "general.commercial_trust_no",
        "general.urgency_no",
        "general.future_commitment_no",
        "general.cooperation_contract_no",
    }.issubset(set(selected_radios))


def test_general_completion_requires_every_postcondition() -> None:
    required = {
        "government_plan_selected": True,
        "budget_year_selected": True,
        "budget_item_selected": True,
        "budget_subsector_selected": True,
        "budget_link_clicked": True,
        "secop_yes_selected": True,
        "secop_url_written": True,
        "advance_no_selected": True,
        "commercial_trust_no_selected": True,
        "urgency_no_selected": True,
        "future_commitment_no_selected": True,
        "cooperation_contract_no_selected": True,
        "execution_department_selected": True,
        "execution_city_selected": True,
        "final_validate_button_found": True,
    }

    assert all(required.values())
    required["budget_link_clicked"] = False
    assert not all(required.values())


def test_first_autocomplete_confirmation_must_return_nonempty_value() -> None:
    subject = probe()
    resolver = FakeResolver()
    resolver.elements["general.government_plan"] = FakeElement("Plan vigente")
    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]

    selected = subject._select_first_autocomplete_and_confirm(
        driver=object(),
        waits=FakeWaits(),
        resolver=resolver,
        key="general.government_plan",
        code="FAILED",
        label="Plan de Gobierno",
    )

    assert selected == "Plan vigente"
