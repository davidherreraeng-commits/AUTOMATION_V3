from __future__ import annotations

from dataclasses import dataclass

import pytest
from selenium.common.exceptions import TimeoutException

from adapters.portal.gestion_transparente.selenium.verified_selection import (
    VerifiedSelectionInteractor,
    VerifiedSelectionPolicy,
)
from domain.errors import PortalTimeoutError


@dataclass
class SharedState:
    clicks: int = 0
    resolutions: int = 0


class FakeElement:
    def __init__(self, state: SharedState) -> None:
        self._state = state

    def click(self) -> None:
        self._state.clicks += 1


class FakeDriver:
    def execute_script(self, script: str, element: FakeElement) -> None:
        if "click" in script and "scrollIntoView" not in script:
            element.click()


class FakeResolver:
    def __init__(self, state: SharedState) -> None:
        self.state = state
        self.keys: list[str] = []

    def clickable(self, key: str, *, timeout_seconds: float) -> FakeElement:
        self.state.resolutions += 1
        self.keys.append(key)
        return FakeElement(self.state)


class FakeWaits:
    def __init__(self, driver: FakeDriver) -> None:
        self.driver = driver

    def until(self, condition, *, timeout_seconds: float):
        if condition(self.driver):
            return True
        raise TimeoutException("Postcondición pendiente.")


def subject(state: SharedState) -> VerifiedSelectionInteractor:
    driver = FakeDriver()
    return VerifiedSelectionInteractor(
        driver=driver,
        waits=FakeWaits(driver),
        resolver=FakeResolver(state),
        timeout_seconds=20,
    )


def native_policy(attempts: int) -> VerifiedSelectionPolicy:
    return VerifiedSelectionPolicy(
        click_modes=tuple("native" for _ in range(attempts)),
        resolve_timeout_seconds=1,
        postcondition_timeout_seconds=1,
        final_postcondition_timeout_seconds=1,
    )


def test_should_relocate_and_retry_until_semantic_postcondition() -> None:
    state = SharedState()
    selector = subject(state)

    outcome = selector.select(
        trigger_key="project.confirm_button",
        postcondition=lambda driver: state.clicks >= 3,
        error_code="PROJECT_SELECTION_UNCONFIRMED",
        selection_label="Código del Proyecto",
        policy=native_policy(4),
    )

    assert outcome.attempt_count == 3
    assert outcome.click_mode == "native"
    assert state.clicks == 3
    assert state.resolutions == 3


def test_should_skip_click_when_selection_is_already_confirmed() -> None:
    state = SharedState()
    selector = subject(state)

    outcome = selector.select(
        trigger_key="contractor.confirm_button",
        postcondition=lambda driver: True,
        error_code="CONTRACTOR_SELECTION_UNCONFIRMED",
        selection_label="Identificación del Contratista",
        policy=native_policy(2),
    )

    assert outcome.already_selected is True
    assert outcome.attempt_count == 0
    assert state.clicks == 0
    assert state.resolutions == 0


def test_should_report_attempt_metadata_after_retry_budget() -> None:
    state = SharedState()
    selector = subject(state)

    with pytest.raises(PortalTimeoutError) as captured:
        selector.select(
            trigger_key="supervisor.select_button",
            postcondition=lambda driver: False,
            error_code="SUPERVISOR_SELECTION_UNCONFIRMED",
            selection_label="Identificación del Supervisor",
            policy=native_policy(2),
        )

    assert captured.value.code == "SUPERVISOR_SELECTION_UNCONFIRMED"
    assert captured.value.metadata["trigger_key"] == "supervisor.select_button"
    assert captured.value.metadata["attempt_count"] == 2
    assert state.clicks == 2
    assert state.resolutions == 2


@pytest.mark.parametrize(
    ("trigger_key", "label"),
    [
        ("contractor.confirm_button", "Identificación del Contratista"),
        ("project.confirm_button", "Código del Proyecto"),
        ("supervisor.select_button", "Identificación del Supervisor"),
    ],
)
def test_should_support_all_search_selection_flows(
    trigger_key: str,
    label: str,
) -> None:
    state = SharedState()
    selector = subject(state)

    outcome = selector.select(
        trigger_key=trigger_key,
        postcondition=lambda driver: state.clicks >= 1,
        error_code="SELECTION_UNCONFIRMED",
        selection_label=label,
        policy=native_policy(1),
    )

    assert outcome.attempt_count == 1
    assert state.resolutions == 1
