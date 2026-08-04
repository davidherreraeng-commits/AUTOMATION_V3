from __future__ import annotations

from decimal import Decimal

from selenium.common.exceptions import StaleElementReferenceException

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)


class ReplacingElement:
    def __init__(self, resolver, key: str, *, stale_on_tab: bool) -> None:
        self.resolver = resolver
        self.key = key
        self.value = ""
        self.stale_on_tab = stale_on_tab

    @property
    def text(self) -> str:
        return ""

    def clear(self) -> None:
        self.value = ""

    def click(self) -> None:
        return None

    def send_keys(self, value) -> None:
        text = str(value)
        if "\ue004" in text:  # TAB
            replacement = ReplacingElement(
                self.resolver,
                self.key,
                stale_on_tab=False,
            )
            replacement.value = self.value
            self.resolver.current = replacement
            if self.stale_on_tab:
                raise StaleElementReferenceException(
                    "React reemplazó el input"
                )
            return
        self.value += text

    def get_attribute(self, name: str):
        if name == "value":
            return self.value
        return None


class ReplacingResolver:
    def __init__(self, key: str) -> None:
        self.key = key
        self.current = ReplacingElement(
            self,
            key,
            stale_on_tab=True,
        )
        self.clickable_calls = 0

    def clickable(self, key: str, timeout_seconds: float):
        assert key == self.key
        self.clickable_calls += 1
        return self.current

    def optional_visible(self, key: str, timeout_seconds: float):
        assert key == self.key
        return self.current


class ImmediateWaits:
    def until(self, predicate, timeout_seconds: float):
        if predicate(None):
            return True
        raise AssertionError("La postcondición no quedó confirmada")


class Driver:
    def execute_script(self, script: str, element) -> None:
        return None


def subject() -> SeleniumBatchPortalProbe:
    instance = SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=5,
        factory=object(),
    )
    instance._scroll_into_view = lambda *args, **kwargs: None
    return instance


def test_text_field_relocates_after_react_replaces_input() -> None:
    resolver = ReplacingResolver("budget_register.number_input")

    subject()._write_text_field_by_key_and_confirm(
        driver=Driver(),
        waits=ImmediateWaits(),
        resolver=resolver,
        key="budget_register.number_input",
        expected="14",
        code="BUDGET_REGISTER_NUMBER_WRITE_FAILED",
        label="No. Registro Presupuestal",
    )

    assert resolver.current.value == "14"
    assert resolver.clickable_calls == 2


def test_currency_field_relocates_after_react_replaces_input() -> None:
    resolver = ReplacingResolver("budget_register.gross_total_input")

    subject()._write_currency_field_by_key_and_confirm(
        driver=Driver(),
        waits=ImmediateWaits(),
        resolver=resolver,
        key="budget_register.gross_total_input",
        expected=Decimal("1.00"),
        code="BUDGET_REGISTER_GROSS_TOTAL_WRITE_FAILED",
        label="Total Bruto",
    )

    assert resolver.current.value == "1"
    assert resolver.clickable_calls == 2
