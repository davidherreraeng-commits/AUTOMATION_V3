from __future__ import annotations

from dataclasses import dataclass

import pytest
from selenium.common.exceptions import WebDriverException

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from domain.errors import PortalTimeoutError


@dataclass
class FakeElement:
    name: str
    clicks: int = 0

    def click(self) -> None:
        self.clicks += 1


class FakeDriver:
    def __init__(self) -> None:
        self.script_calls: list[str] = []

    def execute_script(self, script: str, element: FakeElement) -> None:
        self.script_calls.append(script)
        if "arguments[0].click" in script:
            element.click()


class FakeResolver:
    def __init__(
        self,
        missing: set[str] | None = None,
        *,
        reveal_contract_number_after_click: bool = True,
    ) -> None:
        self.missing = missing or set()
        self.calls: list[tuple[str, str]] = []
        self.radio = FakeElement("contract.header.record_type_contract")
        self.contract_number = FakeElement(
            "contract.header.contract_number"
        )
        self.reveal_contract_number_after_click = (
            reveal_contract_number_after_click
        )

    def resolve(
        self,
        key: str,
        *,
        condition: str,
        timeout_seconds: float,
        capture_diagnostics: bool,
    ):
        self.calls.append((key, condition))
        if key in self.missing:
            raise PortalTimeoutError(f"No existe {key}.")
        return FakeElement(key)

    def presence(
        self,
        key: str,
        *,
        timeout_seconds: float,
    ) -> FakeElement:
        self.calls.append((key, "presence"))
        if key in self.missing:
            raise PortalTimeoutError(f"No existe {key}.")
        if key == "contract.header.record_type_contract":
            return self.radio
        return FakeElement(key)

    def optional_visible(
        self,
        key: str,
        *,
        timeout_seconds: float,
    ) -> FakeElement | None:
        self.calls.append((key, "optional_visible"))
        if key in self.missing:
            return None
        if key == "contract.header.contract_number":
            if (
                self.reveal_contract_number_after_click
                and self.radio.clicks > 0
            ):
                return self.contract_number
            return None
        return FakeElement(key)


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def test_should_select_contract_before_inspecting_dependent_controls() -> None:
    resolver = FakeResolver()
    driver = FakeDriver()

    contract_number = probe()._select_contract_record_type(
        driver=driver,
        resolver=resolver,
    )

    assert resolver.radio.clicks == 1
    assert contract_number is resolver.contract_number
    assert resolver.calls[0] == (
        "contract.header.record_type_contract",
        "presence",
    )
    assert (
        "contract.header.contract_number",
        "optional_visible",
    ) in resolver.calls


def test_should_click_contract_even_when_radio_was_already_present() -> None:
    resolver = FakeResolver()

    probe()._select_contract_record_type(
        driver=FakeDriver(),
        resolver=resolver,
    )

    # La sola presencia del radio no equivale a que React haya montado
    # los campos; el flujo debe pulsarlo explícitamente.
    assert resolver.radio.clicks == 1


def test_should_use_click_fallbacks_for_contract_radio() -> None:
    resolver = FakeResolver()
    subject = probe()
    attempts: list[str] = []

    def perform_click(*, driver, element, mode: str) -> None:
        attempts.append(mode)
        if mode != "javascript":
            raise WebDriverException(f"fallo {mode}")
        element.click()

    subject._perform_click = perform_click  # type: ignore[method-assign]

    subject._select_contract_record_type(
        driver=FakeDriver(),
        resolver=resolver,
    )

    assert attempts == ["native", "actions", "javascript"]
    assert resolver.radio.clicks == 1


def test_should_raise_specific_error_when_contract_form_does_not_render() -> None:
    resolver = FakeResolver(reveal_contract_number_after_click=False)
    subject = probe()

    def perform_click(*, driver, element, mode: str) -> None:
        element.click()

    subject._perform_click = perform_click  # type: ignore[method-assign]

    with pytest.raises(PortalTimeoutError) as captured:
        subject._select_contract_record_type(
            driver=FakeDriver(),
            resolver=resolver,
        )

    assert captured.value.code == "CONTRACT_RECORD_TYPE_SELECTION_TIMEOUT"
    assert resolver.radio.clicks == 3


def test_should_confirm_all_c1_c2_controls_after_activation() -> None:
    resolver = FakeResolver()

    flags, missing = probe()._inspect_header_controls(resolver)

    assert all(flags.values())
    assert missing == ()
    assert (
        "contract.header.record_type_contract",
        "presence",
    ) in resolver.calls
    assert (
        "contract.header.contractor_link",
        "clickable",
    ) in resolver.calls
    assert (
        "contract.header.validate_button",
        "clickable",
    ) in resolver.calls


def test_should_report_each_missing_control_with_safe_label() -> None:
    resolver = FakeResolver(
        {
            "contract.header.contract_number",
            "contract.header.project_link",
        }
    )

    flags, missing = probe()._inspect_header_controls(resolver)

    assert flags["contract_number_found"] is False
    assert flags["project_search_found"] is False
    assert flags["record_type_found"] is True
    assert missing == (
        "Número del contrato",
        "Búsqueda de proyecto",
    )


def test_header_inspection_should_not_write_or_click_form_controls() -> None:
    resolver = FakeResolver()

    probe()._inspect_header_controls(resolver)

    assert len(resolver.calls) == 5
    assert resolver.radio.clicks == 0
    assert {condition for _, condition in resolver.calls} == {
        "presence",
        "visible",
        "clickable",
    }
