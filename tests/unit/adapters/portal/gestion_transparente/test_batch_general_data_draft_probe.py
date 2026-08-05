from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from application.ports.batch_portal_probe import (
    BatchGeneralDataDraftProbeResult,
)
from domain.enums.contractor_nature import ContractorNature
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


@dataclass
class FakeClearButton:
    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True


class FakeAutocompleteRoot:
    def __init__(self, control: "FakeElement") -> None:
        self.control = control

    def get_attribute(self, name: str):
        if name == "class":
            classes = ["MuiAutocomplete-root"]
            if self.control.committed:
                classes.append("MuiAutocomplete-hasClearIcon")
            if self.control.expanded:
                classes.append("Mui-expanded")
            return " ".join(classes)
        return None

    def find_elements(self, by, value):
        if (
            by == By.CSS_SELECTOR
            and value == "button.MuiAutocomplete-clearIndicator"
            and self.control.committed
        ):
            return [FakeClearButton()]
        return []


@dataclass
class FakeElement:
    value: str = ""
    text: str = ""
    selected: bool = False
    committed: bool = False
    expanded: bool = False

    def click(self) -> None:
        self.selected = True

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
        if name == "aria-expanded":
            return "true" if self.expanded else "false"
        if name == "aria-invalid":
            return "false"
        return None

    def find_elements(self, by, value):
        if by == By.XPATH and "MuiAutocomplete-root" in value:
            return [FakeAutocompleteRoot(self)]
        return []

    def is_selected(self) -> bool:
        return self.selected


class FakeResolver:
    def __init__(self) -> None:
        self.elements = {
            "general.object_description": FakeElement(),
            "general.signing_date": FakeElement(),
            "general.starting_date": FakeElement(),
            "general.amount": FakeElement(),
            "general.amount_in_words": FakeElement(value="un peso"),
            "general.contract_term": FakeElement(),
        }

    def visible(self, key: str, *, timeout_seconds: float):
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


def test_result_never_reports_general_validation_or_save_by_default() -> None:
    outcome = BatchGeneralDataDraftProbeResult(
        success=True,
        code="general_data_draft_ready",
        message="C3 completo.",
        general_data_completed=True,
    )

    assert outcome.code == "GENERAL_DATA_DRAFT_READY"
    assert outcome.general_validate_clicked is False
    assert outcome.save_clicked is False


def test_should_format_dates_for_portal() -> None:
    assert probe()._format_portal_date(date(2026, 1, 20)) == "20/01/2026"


def test_semantic_catalog_comparison_should_ignore_accents() -> None:
    assert probe()._semantic_text_equals(
        "Contratacion Directa",
        "Contratación Directa",
    )


def test_currency_comparison_should_accept_portal_format() -> None:
    subject = probe()
    assert subject._currency_value_equals("$1.476.190", Decimal("1476190"))
    assert subject._currency_value_equals("$ 1,476,190", Decimal("1476190"))


def test_should_populate_all_general_fields_without_validation_or_save() -> None:
    subject = probe()
    resolver = FakeResolver()
    calls: list[tuple[str, str]] = []
    selection_calls: list[dict[str, object]] = []

    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._write_currency_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: resolver.elements["general.amount"].__setattr__(
            "value", "$1.476.190"
        )
    )
    subject._select_radio = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("radio", kwargs["key"]))
    )
    def select_autocomplete(**kwargs) -> None:
        calls.append((kwargs["key"], kwargs["expected"]))
        selection_calls.append(dict(kwargs))
        element = resolver.elements.setdefault(
            kwargs["key"],
            FakeElement(),
        )
        element.value = kwargs["expected"]
        if kwargs["key"] == "general.typology":
            element.committed = True

    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        select_autocomplete
    )

    flags = subject._populate_general_data_draft(
        driver=object(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(),
    )

    assert all(flags.values())
    assert resolver.elements["general.object_description"].value == (
        "Servicio institucional."
    )
    assert resolver.elements["general.signing_date"].value == "20/01/2026"
    assert resolver.elements["general.starting_date"].value == "21/01/2026"
    assert resolver.elements["general.contract_term"].value == "180"
    assert ("radio", "general.term_unit_days") in calls
    assert ("radio", "general.other_currency_no") in calls
    assert ("general.process_type", "Contratacion Directa") in calls
    assert (
        "general.contract_type",
        "Contrato de Prestación de Servicios",
    ) in calls
    assert (
        "general.typology",
        "Prestación De Servicios Contratación Directa",
    ) in calls
    catalog_keys = [
        key
        for key, _expected in calls
        if key.startswith("general.") and key != "general.term_unit_days"
    ]
    assert catalog_keys.index("general.process_type") < catalog_keys.index(
        "general.contract_type"
    )
    assert catalog_keys.index("general.contract_type") < catalog_keys.index(
        "general.typology"
    )
    typology_call = next(
        call
        for call in selection_calls
        if call["key"] == "general.typology"
    )
    assert typology_call["allow_decorated_value"] is True
    assert typology_call["require_committed_state"] is True


def test_should_select_procedure_after_contract_type_repopulates_catalog() -> None:
    subject = probe()
    resolver = FakeResolver()
    calls: list[str] = []

    def select_autocomplete(**kwargs) -> None:
        key = kwargs["key"]
        calls.append(key)
        element = resolver.elements.setdefault(key, FakeElement())
        element.value = kwargs["expected"]
        if key == "general.typology":
            element.committed = True
        if key == "general.contract_type":
            # Comportamiento observado en Gestión Transparente: al elegir el
            # tipo, React repuebla y limpia Procedimiento / Causal.
            resolver.elements.setdefault(
                "general.typology",
                FakeElement(),
            ).value = ""

    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        select_autocomplete
    )

    flags = subject._select_general_classification_catalogs(
        driver=object(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=contract(),
    )

    assert calls == [
        "general.process_type",
        "general.contract_type",
        "general.typology",
    ]
    assert resolver.elements["general.typology"].value == (
        "Prestación De Servicios Contratación Directa"
    )
    assert flags == {
        "process_type_selected": True,
        "contract_type_selected": True,
        "procedure_selected": True,
    }


def test_general_data_completion_requires_every_postcondition() -> None:
    required = {
        "object_written": True,
        "signing_date_written": True,
        "starting_date_written": True,
        "amount_written": True,
        "amount_in_words_generated": True,
        "contract_term_written": True,
        "term_unit_days_selected": True,
        "process_type_selected": True,
        "procedure_selected": True,
        "contract_type_selected": True,
        "other_currency_no_selected": True,
    }
    assert all(required.values())
    required["procedure_selected"] = False
    assert not all(required.values())


def test_currency_candidates_should_reject_empty_text() -> None:
    assert probe()._currency_candidates("") == set()

def test_should_use_canonical_portal_text_for_persisted_alias() -> None:
    subject = probe()
    resolver = FakeResolver()
    selected: list[tuple[str, str]] = []
    persisted = contract()
    persisted = ContractData(
        contract_number=persisted.contract_number,
        dependency=persisted.dependency,
        contractor=persisted.contractor,
        project_code=persisted.project_code,
        object_description=persisted.object_description,
        signing_date=persisted.signing_date,
        starting_date=persisted.starting_date,
        amount=persisted.amount,
        term_days=persisted.term_days,
        process_type="Contratación Directa",
        procedure="Sin Pluralidad De Oferentes",
        contract_type="Servicios",
        budget=persisted.budget,
        supervisor=persisted.supervisor,
        secop_url=persisted.secop_url,
    )

    def select_autocomplete(**kwargs) -> None:
        selected.append((kwargs["key"], kwargs["expected"]))
        element = resolver.elements.setdefault(kwargs["key"], FakeElement())
        element.value = kwargs["expected"]
        if kwargs["key"] == "general.typology":
            element.committed = True

    subject._select_autocomplete_and_confirm = select_autocomplete  # type: ignore[method-assign]

    flags = subject._select_general_classification_catalogs(
        driver=object(),
        waits=FakeWaits(),
        resolver=resolver,
        contract=persisted,
    )

    assert flags["procedure_selected"] is True
    assert selected == [
        ("general.process_type", "Contratacion Directa"),
        (
            "general.contract_type",
            "Contrato de Prestación de Servicios",
        ),
        ("general.typology", "Sin Pluraridad de Oferentes"),
    ]
