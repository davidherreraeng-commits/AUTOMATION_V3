from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from adapters.portal.gestion_transparente import batch_portal_probe as probe_module
from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchContractSupervisorLinkProbeResult,
)
from domain.enums.contractor_nature import ContractorNature
from domain.errors import PortalTimeoutError
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


class FakeElement:
    def __init__(self, value: str = "", text: str = "") -> None:
        self.value = value
        self.text = text
        self.clicks = 0

    def click(self) -> None:
        self.clicks += 1

    def clear(self) -> None:
        self.value = ""

    def send_keys(self, *values) -> None:
        self.value += "".join(str(value) for value in values if len(str(value)) == 1)

    def get_attribute(self, name: str):
        if name == "value":
            return self.value
        return None


class FakeResolver:
    def __init__(self) -> None:
        self.document = FakeElement("71693738")
        self.search = FakeElement(text="BUSCAR")
        self.result = FakeElement(text="71693738 ISABELA AMARILES QUICENO")
        self.accept = FakeElement()
        self.linked = FakeElement(text="Disponibilidad presupuestal")

    def clickable(self, key: str, **kwargs):
        if key == "supervisor.document_input":
            return self.document
        if key == "supervisor.search_button":
            return self.search
        if key == "supervisor.link_success_accept":
            return self.accept
        raise AssertionError(key)

    def visible(self, key: str, **kwargs):
        if key == "supervisor.result_row":
            return self.result
        raise AssertionError(key)

    def optional_visible(self, key: str, **kwargs):
        if key == "supervisor.linked":
            return self.linked
        if key == "availability.section":
            return None
        raise AssertionError(key)


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def contract(
    *,
    secop_url: str | None = "https://community.secop.gov.co/test",
    supervisor_type: str = "Interno",
) -> ContractData:
    return ContractData(
        contract_number="81-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.NATURAL_PERSON,
            document_number="1042063697",
        ),
        project_code="I-23021-2026",
        object_description="Contrato de prueba para supervisor.",
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
        supervisor=SupervisorData("71693738", supervisor_type),
        secop_url=secop_url,
    )


def test_result_normalizes_code_and_supervisor_flags() -> None:
    outcome = BatchContractSupervisorLinkProbeResult(
        success=True,
        code="contract_supervisor_link_ready",
        message="Vinculado.",
        contract_saved_confirmed=True,
        supervisor_selected=True,
        supervisor_type_internal_confirmed=True,
        supervisor_linked_confirmed=True,
        availability_section_found=True,
    )

    assert outcome.code == "CONTRACT_SUPERVISOR_LINK_READY"
    assert outcome.contract_saved_confirmed is True
    assert outcome.supervisor_selected is True
    assert outcome.supervisor_type_internal_confirmed is True
    assert outcome.supervisor_linked_confirmed is True
    assert outcome.availability_section_found is True


def test_should_reject_missing_secop_before_opening_browser() -> None:
    outcome = probe().probe_contract_supervisor_link(
        portal_username="usuario",
        portal_password="clave",
        contract=contract(secop_url=None),
    )

    assert outcome.success is False
    assert outcome.code == "MISSING_SECOP_URL"
    assert outcome.supervisor_link_clicked is False


def test_should_link_internal_supervisor_and_confirm_availability() -> None:
    subject = probe()
    resolver = FakeResolver()
    clicks: list[tuple[str, str]] = []
    radios: list[str] = []
    autocompletes: list[dict[str, object]] = []
    writes: list[str] = []
    selections: list[str] = []

    subject._click_and_confirm_visible = (  # type: ignore[method-assign]
        lambda **kwargs: clicks.append(
            (kwargs["click_key"], kwargs["target_key"])
        ) or FakeElement()
    )
    subject._select_radio = (  # type: ignore[method-assign]
        lambda **kwargs: radios.append(kwargs["key"])
    )
    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: autocompletes.append(dict(kwargs))
    )
    subject._write_and_confirm_wait = (  # type: ignore[method-assign]
        lambda **kwargs: writes.append(kwargs["expected"])
    )
    subject._confirm_supervisor_selection_with_retries = (  # type: ignore[method-assign]
        lambda **kwargs: selections.append(kwargs["expected_document"])
    )
    subject._resolved_autocomplete_matches = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["expected"] == "Interno"
    )
    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._perform_click = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].click()
    )

    class FakeWaits:
        def until(self, condition, **kwargs):
            assert condition(object()) is True
            return True

    flags = subject._link_supervisor_and_confirm(
        driver=object(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(),
    )

    assert clicks == [
        ("supervisor.search_open", "supervisor.dialog"),
        ("supervisor.validate_button", "supervisor.validation_success"),
        ("supervisor.link_button", "supervisor.link_success_dialog"),
    ]
    assert radios == ["supervisor.nature_person"]
    assert len(autocompletes) == 2
    assert autocompletes[0]["key"] == "supervisor.id_type"
    assert autocompletes[0]["expected"] == "Cedula de Ciudadanía"
    assert autocompletes[0]["alternative_clickable_key"] is None
    assert autocompletes[1]["key"] == "supervisor.type_input"
    assert autocompletes[1]["expected"] == "Interno"
    assert autocompletes[1]["code"] == "SUPERVISOR_TYPE_NOT_INTERNAL"
    assert autocompletes[1]["alternative_clickable_key"] is None
    assert writes == ["71693738"]
    assert selections == ["71693738"]
    assert resolver.search.clicks == 1
    assert all(flags.values())
    assert resolver.accept.clicks == 1


def test_supervisor_selection_uses_shared_verified_pattern(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeSelector:
        def __init__(self, **kwargs) -> None:
            captured["init"] = kwargs

        def select(self, **kwargs):
            captured.update(kwargs)
            return object()

    monkeypatch.setattr(
        probe_module,
        "VerifiedSelectionInteractor",
        FakeSelector,
    )
    subject = probe()
    subject._resolved_identity_matches = (  # type: ignore[method-assign]
        lambda **kwargs: True
    )

    subject._confirm_supervisor_selection_with_retries(
        driver=object(),
        waits=object(),
        resolver=object(),
        expected_document="71693738",
    )

    assert captured["trigger_key"] == "supervisor.select_button"
    assert captured["error_code"] == "SUPERVISOR_SELECTION_UNCONFIRMED"
    assert captured["selection_label"] == "Identificación del Supervisor"
    assert captured["postcondition"](object()) is True


def test_supervisor_link_requires_every_postcondition() -> None:
    flags = {
        "contract_saved_confirmed": True,
        "supervisor_section_found": True,
        "supervisor_dialog_opened": True,
        "supervisor_nature_selected": True,
        "supervisor_id_type_selected": True,
        "supervisor_document_written": True,
        "supervisor_result_found": True,
        "supervisor_selected": True,
        "supervisor_type_internal_confirmed": True,
        "supervisor_validate_clicked": True,
        "supervisor_validation_confirmed": True,
        "supervisor_link_clicked": True,
        "success_dialog_found": True,
        "success_dialog_accepted": True,
        "supervisor_linked_confirmed": True,
        "availability_section_found": True,
    }
    assert all(flags.values())
    flags["availability_section_found"] = False
    assert not all(flags.values())


def test_supervisor_result_wait_retries_and_retypes_until_exact_match() -> None:
    subject = probe()
    document = FakeElement("52263286")
    search = FakeElement(text="BUSCAR")
    exact_row = FakeElement(text="52263286 SUPERVISOR DE PRUEBA")

    class SequenceResolver:
        def __init__(self) -> None:
            self.calls = 0

        def visible(self, key: str, **kwargs):
            assert key == "supervisor.result_row"
            self.calls += 1
            if self.calls < 3:
                raise PortalTimeoutError("Sin fila.", code="PORTAL_TIMEOUT")
            return exact_row

        def clickable(self, key: str, **kwargs):
            if key == "supervisor.document_input":
                return document
            if key == "supervisor.search_button":
                return search
            raise AssertionError(key)

    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._perform_click = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].click()
    )
    resolver = SequenceResolver()
    row = subject._wait_for_supervisor_result_with_retries(
        driver=object(),
        resolver=resolver,
        expected_document="52263286",
    )

    assert row is exact_row
    assert resolver.calls == 3
    assert search.clicks == 3
    assert document.clicks == 2


def test_supervisor_result_wait_reports_not_found_after_three_attempts() -> None:
    subject = probe()
    document = FakeElement("52263286")
    search = FakeElement(text="BUSCAR")

    class EmptyResolver:
        def visible(self, key: str, **kwargs):
            raise PortalTimeoutError("Sin fila.", code="PORTAL_TIMEOUT")

        def clickable(self, key: str, **kwargs):
            if key == "supervisor.document_input":
                return document
            if key == "supervisor.search_button":
                return search
            raise AssertionError(key)

    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._perform_click = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].click()
    )
    with pytest.raises(PortalTimeoutError) as captured:
        subject._wait_for_supervisor_result_with_retries(
            driver=object(),
            resolver=EmptyResolver(),
            expected_document="52263286",
        )

    assert captured.value.code == "SUPERVISOR_RESULT_NOT_FOUND"
    assert "52263286" in str(captured.value)
    assert search.clicks == 3
    assert document.clicks == 2


def test_supervisor_result_wait_reports_mismatch_for_other_identity() -> None:
    subject = probe()
    document = FakeElement("52263286")
    search = FakeElement(text="BUSCAR")
    wrong_row = FakeElement(text="99999999 OTRA PERSONA")

    class WrongResolver:
        def visible(self, key: str, **kwargs):
            return wrong_row

        def clickable(self, key: str, **kwargs):
            if key == "supervisor.document_input":
                return document
            if key == "supervisor.search_button":
                return search
            raise AssertionError(key)

    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._perform_click = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].click()
    )
    with pytest.raises(PortalTimeoutError) as captured:
        subject._wait_for_supervisor_result_with_retries(
            driver=object(),
            resolver=WrongResolver(),
            expected_document="52263286",
        )

    assert captured.value.code == "SUPERVISOR_RESULT_MISMATCH"


def test_supervisor_search_button_uses_click_fallbacks() -> None:
    subject = probe()
    search = FakeElement(text="BUSCAR")
    used_modes: list[str] = []

    class SearchResolver:
        def clickable(self, key: str, **kwargs):
            assert key == "supervisor.search_button"
            return search

    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]

    def click(**kwargs) -> None:
        used_modes.append(kwargs["mode"])
        if kwargs["mode"] != "javascript":
            raise probe_module.WebDriverException("bloqueado")
        kwargs["element"].click()

    subject._perform_click = click  # type: ignore[method-assign]
    subject._click_supervisor_search_button(
        driver=object(),
        resolver=SearchResolver(),
        attempt=1,
    )

    assert used_modes == ["native", "actions", "javascript"]
    assert search.clicks == 1


def test_supervisor_search_button_reports_specific_click_failure() -> None:
    subject = probe()

    class SearchResolver:
        def clickable(self, key: str, **kwargs):
            return FakeElement(text="BUSCAR")

    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._perform_click = (  # type: ignore[method-assign]
        lambda **kwargs: (_ for _ in ()).throw(
            probe_module.WebDriverException("bloqueado")
        )
    )

    with pytest.raises(PortalTimeoutError) as captured:
        subject._click_supervisor_search_button(
            driver=object(),
            resolver=SearchResolver(),
            attempt=2,
        )

    assert captured.value.code == "SUPERVISOR_SEARCH_CLICK_FAILED"
    assert captured.value.metadata["search_attempt"] == 2


def test_partial_supervisor_progress_survives_result_timeout() -> None:
    subject = probe()
    resolver = FakeResolver()
    progress = {
        "contract_saved_confirmed": True,
        "supervisor_section_found": True,
    }

    subject._click_and_confirm_visible = (  # type: ignore[method-assign]
        lambda **kwargs: FakeElement()
    )
    subject._select_radio = lambda **kwargs: None  # type: ignore[method-assign]
    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: None
    )
    subject._write_and_confirm_wait = lambda **kwargs: None  # type: ignore[method-assign]
    subject._wait_for_supervisor_result_with_retries = (  # type: ignore[method-assign]
        lambda **kwargs: (_ for _ in ()).throw(
            PortalTimeoutError(
                "No encontrado.",
                code="SUPERVISOR_RESULT_NOT_FOUND",
            )
        )
    )

    with pytest.raises(PortalTimeoutError):
        subject._link_supervisor_and_confirm(
            driver=object(),
            waits=object(),
            resolver=resolver,
            contract=contract(),
            progress=progress,
        )

    assert progress["contract_saved_confirmed"] is True
    assert progress["supervisor_section_found"] is True
    assert progress["supervisor_dialog_opened"] is True
    assert progress["supervisor_nature_selected"] is True
    assert progress["supervisor_id_type_selected"] is True
    assert progress["supervisor_document_written"] is True
    assert progress["supervisor_result_found"] is False
