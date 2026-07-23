from __future__ import annotations

import pytest

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorNotRegisteredError,
    LocatorRegistry,
    LocatorSpec,
)
from adapters.portal.gestion_transparente.selenium.element_resolver import (
    ElementResolver,
)
from domain.errors import PortalTimeoutError


class FakeElement:
    pass

class FakeDiagnosticEvidence:
    def as_metadata(self):
        return {
            "directory": "diagnostics/test",
            "metadata_path": (
                "diagnostics/test/metadata.json"
            ),
            "screenshot_path": (
                "diagnostics/test/screenshot.png"
            ),
            "page_source_path": (
                "diagnostics/test/page_source.html"
            ),
        }


class FakeDiagnostics:
    def __init__(self) -> None:
        self.capture_calls = []

    def capture(
        self,
        *,
        event,
        metadata=None,
        error=None,
    ):
        self.capture_calls.append(
            {
                "event": event,
                "metadata": metadata,
                "error": error,
            }
        )

        return FakeDiagnosticEvidence()


def test_should_attach_diagnostics_after_resolution_failure(
) -> None:
    registry = LocatorRegistry(
        (
            LocatorSpec(
                key="assistant.open",
                by=By.ID,
                value="missing",
            ),
        )
    )

    waits = FakeWaits()
    diagnostics = FakeDiagnostics()

    resolver = ElementResolver(
        registry=registry,
        waits=waits,
        diagnostics=diagnostics,
    )

    with pytest.raises(
        PortalTimeoutError,
    ) as captured:
        resolver.visible(
            "assistant.open"
        )

    assert len(
        diagnostics.capture_calls
    ) == 1

    assert (
        captured.value.metadata[
            "diagnostics"
        ]["directory"]
        == "diagnostics/test"
    )


def test_optional_resolution_should_not_capture_diagnostics(
) -> None:
    registry = LocatorRegistry(
        (
            LocatorSpec(
                key="optional.element",
                by=By.ID,
                value="missing",
            ),
        )
    )

    waits = FakeWaits()
    diagnostics = FakeDiagnostics()

    resolver = ElementResolver(
        registry=registry,
        waits=waits,
        diagnostics=diagnostics,
    )

    result = resolver.optional_visible(
        "optional.element"
    )

    assert result is None
    assert diagnostics.capture_calls == []


class FakeWaits:
    default_timeout_seconds = 10.0
    poll_frequency_seconds = 0.25

    def __init__(self) -> None:
        self.calls: list[
            tuple[str, tuple[str, str], float]
        ] = []

        self.responses: dict[
            tuple[str, tuple[str, str]],
            object,
        ] = {}

    def _resolve(
        self,
        condition: str,
        locator: tuple[str, str],
        timeout_seconds: float,
    ):
        self.calls.append(
            (
                condition,
                locator,
                timeout_seconds,
            )
        )

        response = self.responses.get(
            (condition, locator)
        )

        if isinstance(response, Exception):
            raise response

        if response is None:
            raise TimeoutException(
                f"No encontrado: {locator}"
            )

        return response

    def presence(
        self,
        locator,
        *,
        timeout_seconds,
    ):
        return self._resolve(
            "presence",
            locator,
            timeout_seconds,
        )

    def visible(
        self,
        locator,
        *,
        timeout_seconds,
    ):
        return self._resolve(
            "visible",
            locator,
            timeout_seconds,
        )

    def clickable(
        self,
        locator,
        *,
        timeout_seconds,
    ):
        return self._resolve(
            "clickable",
            locator,
            timeout_seconds,
        )


def test_should_order_locators_by_priority() -> None:
    registry = LocatorRegistry(
        (
            LocatorSpec(
                key="contract.number",
                by=By.XPATH,
                value="//input[@name='number']",
                priority=20,
            ),
            LocatorSpec(
                key="contract.number",
                by=By.ID,
                value="contractNumber",
                priority=10,
            ),
        )
    )

    candidates = registry.candidates(
        "contract.number"
    )

    assert candidates[0].by == By.ID
    assert candidates[1].by == By.XPATH


def test_should_reject_unknown_locator_key() -> None:
    registry = LocatorRegistry()

    with pytest.raises(
        LocatorNotRegisteredError,
        match="missing.element",
    ):
        registry.candidates(
            "missing.element"
        )


def test_should_use_fallback_locator() -> None:
    first = LocatorSpec(
        key="assistant.open",
        by=By.ID,
        value="oldButton",
        priority=10,
    )

    second = LocatorSpec(
        key="assistant.open",
        by=By.CSS_SELECTOR,
        value="button.open-assistant",
        priority=20,
    )

    registry = LocatorRegistry(
        (first, second)
    )

    waits = FakeWaits()
    element = FakeElement()

    waits.responses[
        ("clickable", first.locator)
    ] = TimeoutException("Primer locator falló")

    waits.responses[
        ("clickable", second.locator)
    ] = element

    resolver = ElementResolver(
        registry=registry,
        waits=waits,
    )

    resolved = resolver.clickable(
        "assistant.open"
    )

    assert resolved is element

    assert [
        call[1]
        for call in waits.calls
    ] == [
        first.locator,
        second.locator,
    ]


def test_should_raise_portal_timeout_after_all_candidates(
) -> None:
    registry = LocatorRegistry(
        (
            LocatorSpec(
                key="assistant.open",
                by=By.ID,
                value="first",
                priority=10,
            ),
            LocatorSpec(
                key="assistant.open",
                by=By.ID,
                value="second",
                priority=20,
            ),
        )
    )

    waits = FakeWaits()

    resolver = ElementResolver(
        registry=registry,
        waits=waits,
    )

    with pytest.raises(
        PortalTimeoutError,
        match="ninguno de sus localizadores",
    ) as captured:
        resolver.visible(
            "assistant.open",
            timeout_seconds=4,
        )

    assert captured.value.retryable
    assert captured.value.metadata[
        "locator_key"
    ] == "assistant.open"

    assert len(
        captured.value.metadata["attempts"]
    ) == 2