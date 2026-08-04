from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from domain.enums.contractor_nature import ContractorNature
from domain.errors import PortalTimeoutError
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData


class FakeElement:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.clicks = 0

    def get_attribute(self, name: str):
        if name == "value":
            return self.value
        return None

    def click(self) -> None:
        self.clicks += 1


class FakeResolver:
    def __init__(self) -> None:
        self.elements: dict[str, FakeElement] = {}
        self.clickable_calls: list[str] = []

    def visible(self, key: str, *, timeout_seconds: float):
        return self.elements.setdefault(key, FakeElement())

    def clickable(self, key: str, *, timeout_seconds: float):
        self.clickable_calls.append(key)
        return self.elements.setdefault(key, FakeElement())


class FailingResolver(FakeResolver):
    def clickable(self, key: str, *, timeout_seconds: float):
        raise RuntimeError("disabled")


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


def test_budget_item_should_accept_portal_decorated_value() -> None:
    subject = probe()
    resolver = FakeResolver()
    resolver.elements["general.budget_item"] = FakeElement(
        "IDEA-2026 - Inversión institucional"
    )

    assert subject._resolved_autocomplete_matches(
        resolver=resolver,
        key="general.budget_item",
        expected="IDEA-2026",
        allow_decorated_value=True,
    )


def test_subsector_should_accept_code_and_description() -> None:
    subject = probe()
    resolver = FakeResolver()
    resolver.elements["general.budget_subsector"] = FakeElement(
        "01 - Tecnología"
    )

    assert subject._resolved_autocomplete_matches(
        resolver=resolver,
        key="general.budget_subsector",
        expected="Tecnología",
        allow_decorated_value=True,
    )


def test_dependent_subsector_must_be_clickable_before_selection() -> None:
    subject = probe()
    resolver = FakeResolver()

    element = subject._wait_for_dependent_autocomplete(
        resolver=resolver,
        key="general.budget_subsector",
        code="GENERAL_BUDGET_SUBSECTOR_NOT_READY",
        label="Sub-Sector",
        dependency_label="Rubro Presupuestal",
    )

    assert element is resolver.elements["general.budget_subsector"]
    assert resolver.clickable_calls == ["general.budget_subsector"]


def test_dependent_subsector_should_report_specific_not_ready_error() -> None:
    subject = probe()

    with pytest.raises(PortalTimeoutError) as captured:
        subject._wait_for_dependent_autocomplete(
            resolver=FailingResolver(),
            key="general.budget_subsector",
            code="GENERAL_BUDGET_SUBSECTOR_NOT_READY",
            label="Sub-Sector",
            dependency_label="Rubro Presupuestal",
        )

    assert captured.value.code == "GENERAL_BUDGET_SUBSECTOR_NOT_READY"
    assert "Rubro Presupuestal" in str(captured.value)


def test_c4_budget_cascade_uses_decorated_confirmation_and_waits_subsector() -> None:
    subject = probe()
    resolver = FakeResolver()
    calls: list[tuple[str, object]] = []

    subject._select_first_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: "Plan vigente"
    )
    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(
            (
                kwargs["key"],
                kwargs.get("allow_decorated_value", False),
                kwargs.get("alternative_clickable_key"),
            )
        )
    )
    subject._wait_for_dependent_autocomplete = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("wait", kwargs["key"]))
        or FakeElement()
    )
    subject._select_radio = lambda **kwargs: None  # type: ignore[method-assign]
    subject._write_and_confirm_wait = lambda **kwargs: None  # type: ignore[method-assign]
    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._click_with_fallbacks = lambda **kwargs: None  # type: ignore[method-assign]

    subject._populate_general_completion_draft(
        driver=object(),
        waits=object(),
        resolver=resolver,
        contract=contract(),
    )

    assert (
        "general.budget_item",
        True,
        None,
    ) in calls
    assert ("wait", "general.budget_subsector") in calls
    assert (
        "general.budget_subsector",
        True,
        None,
    ) in calls
    assert calls.index(
        (
            "general.budget_item",
            True,
            None,
        )
    ) < calls.index(
        ("wait", "general.budget_subsector")
    ) < calls.index(
        (
            "general.budget_subsector",
            True,
            None,
        )
    )

    assert (
        "general.execution_department",
        True,
        None,
    ) in calls
    assert ("wait", "general.execution_city") in calls
    assert (
        "general.execution_city",
        True,
        None,
    ) in calls
    assert calls.index(
        (
            "general.execution_department",
            True,
            None,
        )
    ) < calls.index(
        ("wait", "general.execution_city")
    ) < calls.index(
        (
            "general.execution_city",
            True,
            None,
        )
    )


def test_budget_item_cannot_be_confirmed_by_enabled_subsector() -> None:
    subject = probe()
    resolver = FakeResolver()
    resolver.elements["general.budget_item"] = FakeElement("")
    resolver.elements["general.budget_subsector"] = FakeElement("")

    assert not subject._autocomplete_selection_confirmed(
        resolver=resolver,
        key="general.budget_item",
        expected="IDEA-2026",
        allow_decorated_value=True,
        alternative_clickable_key="general.budget_subsector",
    )
    assert resolver.clickable_calls == []


def test_subsector_cannot_be_confirmed_by_enabled_budget_link() -> None:
    subject = probe()
    resolver = FakeResolver()
    resolver.elements["general.budget_subsector"] = FakeElement("")
    resolver.elements["general.budget_link_button"] = FakeElement("")

    assert not subject._autocomplete_selection_confirmed(
        resolver=resolver,
        key="general.budget_subsector",
        expected="Tecnología",
        allow_decorated_value=True,
        alternative_clickable_key="general.budget_link_button",
    )
    assert resolver.clickable_calls == []


def test_autocomplete_without_value_or_downstream_state_is_not_confirmed() -> None:
    subject = probe()

    assert not subject._autocomplete_selection_confirmed(
        resolver=FailingResolver(),
        key="general.budget_item",
        expected="IDEA-2026",
        allow_decorated_value=True,
        alternative_clickable_key="general.budget_subsector",
    )


def test_budget_catalog_chain_waits_for_each_dependent_control() -> None:
    subject = probe()
    calls: list[tuple[str, str]] = []

    subject._select_first_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("select", kwargs["key"]))
        or "Plan vigente"
    )
    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("select", kwargs["key"]))
    )
    subject._wait_for_dependent_autocomplete = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append(("wait", kwargs["key"]))
        or FakeElement()
    )

    subject._prepare_budget_catalog_chain(
        driver=object(),
        waits=object(),
        resolver=FakeResolver(),
        budget_year="2026",
    )

    assert calls == [
        ("select", "general.government_plan"),
        ("wait", "general.budget_year"),
        ("select", "general.budget_year"),
        ("wait", "general.budget_item"),
    ]


def test_budget_catalog_chain_retries_from_plan_when_budget_item_is_not_ready() -> None:
    subject = probe()
    plan_attempts = 0
    item_waits = 0

    def select_plan(**kwargs):
        nonlocal plan_attempts
        plan_attempts += 1
        return "Plan vigente"

    def wait_dependent(**kwargs):
        nonlocal item_waits
        if kwargs["key"] == "general.budget_item":
            item_waits += 1
            if item_waits == 1:
                raise PortalTimeoutError(
                    "Rubro no disponible.",
                    code="GENERAL_BUDGET_ITEM_NOT_READY",
                )
        return FakeElement()

    subject._select_first_autocomplete_and_confirm = select_plan  # type: ignore[method-assign]
    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: None
    )
    subject._wait_for_dependent_autocomplete = wait_dependent  # type: ignore[method-assign]

    subject._prepare_budget_catalog_chain(
        driver=object(),
        waits=object(),
        resolver=FakeResolver(),
        budget_year="2026",
    )

    assert plan_attempts == 2
    assert item_waits == 2


def test_budget_catalog_chain_reports_specific_error_after_retry_budget() -> None:
    subject = probe()

    subject._select_first_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: "Plan vigente"
    )
    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: None
    )
    subject._wait_for_dependent_autocomplete = (  # type: ignore[method-assign]
        lambda **kwargs: (_ for _ in ()).throw(
            PortalTimeoutError(
                "Dependencia no habilitada.",
                code="GENERAL_BUDGET_ITEM_NOT_READY",
            )
        )
    )

    with pytest.raises(PortalTimeoutError) as captured:
        subject._prepare_budget_catalog_chain(
            driver=object(),
            waits=object(),
            resolver=FakeResolver(),
            budget_year="2026",
        )

    assert captured.value.code == "GENERAL_BUDGET_CATALOG_NOT_READY"
    assert len(captured.value.metadata["cascade_attempts"]) == 3


def test_general_completion_uses_stabilized_plan_year_budget_chain() -> None:
    subject = probe()
    resolver = FakeResolver()
    calls: list[str] = []

    subject._prepare_budget_catalog_chain = (  # type: ignore[method-assign]
        lambda **kwargs: calls.append("catalog_chain")
    )
    subject._select_autocomplete_and_confirm = (  # type: ignore[method-assign]
        lambda **kwargs: None
    )
    subject._wait_for_dependent_autocomplete = (  # type: ignore[method-assign]
        lambda **kwargs: FakeElement()
    )
    subject._select_radio = lambda **kwargs: None  # type: ignore[method-assign]
    subject._write_and_confirm_wait = lambda **kwargs: None  # type: ignore[method-assign]
    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._click_with_fallbacks = lambda **kwargs: None  # type: ignore[method-assign]

    flags = subject._populate_general_completion_draft(
        driver=object(),
        waits=object(),
        resolver=resolver,
        contract=contract(),
    )

    assert calls == ["catalog_chain"]
    assert flags["government_plan_selected"]
    assert flags["budget_year_selected"]
