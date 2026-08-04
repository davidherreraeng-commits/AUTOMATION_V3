from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from domain.enums.contractor_nature import ContractorNature
from domain.errors import PortalTimeoutError
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


@dataclass
class FakeElement:
    value: str = ""
    text: str = ""
    clicks: int = 0
    selected: bool = False

    def clear(self) -> None:
        self.value = ""

    def click(self) -> None:
        self.clicks += 1
        self.selected = True

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

    def is_selected(self) -> bool:
        return self.selected


class FakeResolver:
    def __init__(self, *, legal: bool = True, mismatch: bool = False) -> None:
        document = "900469775-8" if legal else "1001360022"
        result_document = "999999999-9" if mismatch else document
        self.elements = {
            "contractor.legal.id_type": FakeElement(),
            "contractor.natural.id_type": FakeElement(),
            "contractor.legal.document_input": FakeElement(),
            "contractor.natural.document_input": FakeElement(),
            "contractor.search_button": FakeElement(),
            "contractor.result_row": FakeElement(text=f"{result_document} Contratista"),
            "contractor.confirm_button": FakeElement(),
            "project.code_input": FakeElement(),
            "project.search_button": FakeElement(),
            "project.result_row": FakeElement(text="I-23021-2026 Proyecto"),
            "project.confirm_button": FakeElement(),
        }
        self.calls: list[tuple[str, str]] = []

    def visible(self, key: str, *, timeout_seconds: float):
        self.calls.append((key, "visible"))
        return self.elements[key]

    def clickable(self, key: str, *, timeout_seconds: float):
        self.calls.append((key, "clickable"))
        return self.elements[key]


class FakeDriver:
    def execute_script(self, script: str, element: FakeElement):
        if "click" in script:
            element.click()
        if "checked" in script:
            return element.selected
        return None


class FakeWaits:
    def until(self, condition, *, timeout_seconds: float):
        assert condition(object()) is True
        return True


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def contract(*, legal: bool = True) -> ContractData:
    return ContractData(
        contract_number="70-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=(
                ContractorNature.LEGAL_ENTITY
                if legal
                else ContractorNature.NATURAL_PERSON
            ),
            document_number="900469775-8" if legal else "1001360022",
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
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Interno",
        ),
        secop_url="https://community.secop.gov.co/example",
    )


def prepare_subject(subject: SeleniumBatchPortalProbe, calls: list) -> None:
    subject._click_and_confirm_visible = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("open", kwargs["target_key"]))
    )
    subject._select_radio = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("radio", kwargs["key"]))
    )
    subject._confirm_dialog_selection = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(
            ("confirm-selection", kwargs["trigger_key"])
        )
    )
    subject._click_with_fallbacks = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].click()
    )


def test_should_write_contract_number_and_confirm_value() -> None:
    element = FakeElement()

    probe()._write_and_confirm(
        element=element,
        expected="70-2026",
        code="WRITE_FAILED",
        label="Número",
    )

    assert element.value == "70-2026"


def test_should_normalize_document_punctuation_for_confirmation() -> None:
    subject = probe()

    assert subject._identity_equals("900.469.775-8", "900469775-8") is True
    assert subject._identity_contains("NIT 9004697758", "900469775-8") is True


def test_should_use_legal_contractor_flow_when_document_has_legal_nature() -> None:
    subject = probe()
    resolver = FakeResolver(legal=True)
    calls: list[tuple[str, str]] = []
    prepare_subject(subject, calls)

    flags = subject._select_contractor_draft(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(legal=True),
    )

    assert ("radio", "contractor.nature.legal") in calls
    assert ("contractor.legal.id_type", "visible") in resolver.calls
    assert resolver.elements["contractor.legal.document_input"].value == "900469775-8"
    assert flags["contractor_selected"] is True


def test_should_use_natural_contractor_flow_without_hyphen() -> None:
    subject = probe()
    resolver = FakeResolver(legal=False)
    calls: list[tuple[str, str]] = []
    prepare_subject(subject, calls)

    flags = subject._select_contractor_draft(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(legal=False),
    )

    assert ("radio", "contractor.nature.natural") in calls
    assert ("contractor.natural.id_type", "visible") in resolver.calls
    assert resolver.elements["contractor.natural.document_input"].value == "1001360022"
    assert flags["contractor_selected"] is True


def test_should_reject_contractor_result_that_does_not_match_document() -> None:
    subject = probe()
    resolver = FakeResolver(legal=True, mismatch=True)
    calls: list[tuple[str, str]] = []
    prepare_subject(subject, calls)

    with pytest.raises(PortalTimeoutError) as captured:
        subject._select_contractor_draft(
            driver=FakeDriver(),
            waits=FakeWaits(),
            resolver=resolver,
            contract=contract(legal=True),
        )

    assert captured.value.code == "CONTRACTOR_RESULT_MISMATCH"
    assert resolver.elements["contractor.confirm_button"].clicks == 0


def test_should_search_and_select_exact_project() -> None:
    subject = probe()
    resolver = FakeResolver()
    calls: list[tuple[str, str]] = []
    prepare_subject(subject, calls)

    flags = subject._select_project_draft(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=resolver,
        project_code="I-23021-2026",
    )

    assert resolver.elements["project.code_input"].value == "I-23021-2026"
    assert flags["project_result_found"] is True
    assert flags["project_selected"] is True


def test_header_draft_result_must_report_validate_as_not_clicked() -> None:
    from application.ports.batch_portal_probe import BatchHeaderDraftProbeResult

    outcome = BatchHeaderDraftProbeResult(
        success=True,
        code="HEADER_DRAFT_READY",
        message="Encabezado cargado sin validar.",
        validate_button_found=True,
    )

    assert outcome.validate_button_found is True
    assert outcome.validate_clicked is False


def test_contractor_selection_uses_shared_verified_pattern() -> None:
    subject = probe()
    captured: dict[str, object] = {}
    subject._confirm_dialog_selection = (  # type: ignore[method-assign]
        lambda **kwargs: captured.update(kwargs)
    )

    subject._confirm_contractor_selection_with_retries(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=FakeResolver(),
        expected_document="900469775-8",
    )

    assert captured["trigger_key"] == "contractor.confirm_button"
    assert captured["label"] == "Identificación del Contratista"
    assert captured["error_code"] == "CONTRACTOR_SELECTION_UNCONFIRMED"
    assert captured["identity"] is True


def test_project_selection_uses_shared_verified_pattern() -> None:
    subject = probe()
    captured: dict[str, object] = {}
    subject._confirm_dialog_selection = (  # type: ignore[method-assign]
        lambda **kwargs: captured.update(kwargs)
    )

    subject._confirm_project_selection_with_retries(
        driver=FakeDriver(),
        waits=FakeWaits(),
        resolver=FakeResolver(),
        expected_project_code="I-23021-2026",
    )

    assert captured["trigger_key"] == "project.confirm_button"
    assert captured["label"] == "Código del Proyecto"
    assert captured["error_code"] == "PROJECT_SELECTION_UNCONFIRMED"
    assert captured["identity"] is False
