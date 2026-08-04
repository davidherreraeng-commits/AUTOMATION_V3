from __future__ import annotations

from dataclasses import dataclass

import pytest

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
        self.scripts: list[str] = []

    def execute_script(self, script: str, *args):
        self.scripts.append(script)
        if "arguments[0].click" in script and args:
            args[0].click()
        return None


class FakeResolver:
    def __init__(
        self,
        *,
        target_visible_initially: bool = False,
        target_visible_after_click: bool = False,
    ) -> None:
        self.toggle = FakeElement("toggle")
        self.target = FakeElement("target")
        self.target_visible = target_visible_initially
        self.target_visible_after_click = target_visible_after_click
        self.clickable_calls = 0
        self.optional_calls = 0

    def optional_visible(self, key: str, *, timeout_seconds: float):
        self.optional_calls += 1
        if self.target_visible:
            return self.target
        if self.target_visible_after_click and self.toggle.clicks > 0:
            self.target_visible = True
            return self.target
        return None

    def clickable(self, key: str, *, timeout_seconds: float):
        self.clickable_calls += 1
        return self.toggle


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=9,
        factory=object(),
    )


def test_should_not_click_when_next_menu_level_is_already_visible() -> None:
    resolver = FakeResolver(target_visible_initially=True)

    target = probe()._ensure_target_visible(
        driver=FakeDriver(),
        resolver=resolver,
        toggle_key="navigation.contracting_menu",
        target_key="navigation.enter_contract",
        step_code="TEST_TIMEOUT",
        step_label="Contratación",
    )

    assert target is resolver.target
    assert resolver.toggle.clicks == 0
    assert resolver.clickable_calls == 0


def test_should_click_closed_menu_and_confirm_postcondition() -> None:
    resolver = FakeResolver(target_visible_after_click=True)

    target = probe()._ensure_target_visible(
        driver=FakeDriver(),
        resolver=resolver,
        toggle_key="navigation.contracting_menu",
        target_key="navigation.enter_contract",
        step_code="TEST_TIMEOUT",
        step_label="Contratación",
    )

    assert target is resolver.target
    assert resolver.toggle.clicks == 1
    assert resolver.clickable_calls == 1


def test_should_raise_step_specific_timeout_after_all_click_modes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = FakeResolver()

    def fake_perform_click(*, driver, element, mode: str) -> None:
        # Esta prueba valida la orquestación de los tres fallbacks.
        # ActionChains exige un WebElement real, mientras que el doble de
        # prueba es deliberadamente liviano. La implementación concreta de
        # cada modo pertenece a Selenium y no se prueba aquí.
        element.click()

    monkeypatch.setattr(
        SeleniumBatchPortalProbe,
        "_perform_click",
        staticmethod(fake_perform_click),
    )

    with pytest.raises(PortalTimeoutError) as captured:
        probe()._ensure_target_visible(
            driver=FakeDriver(),
            resolver=resolver,
            toggle_key="navigation.enter_contract",
            target_key="assistant.open",
            step_code="ENTER_CONTRACT_EXPANSION_TIMEOUT",
            step_label="Ingresar Contrato",
        )

    assert captured.value.code == "ENTER_CONTRACT_EXPANSION_TIMEOUT"
    assert resolver.toggle.clicks == 3
    assert len(captured.value.metadata["click_attempts"]) == 3
