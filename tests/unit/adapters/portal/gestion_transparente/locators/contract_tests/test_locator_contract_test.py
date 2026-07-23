from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorRegistry,
    LocatorSpec,
)
from adapters.portal.gestion_transparente.locators.contract_tests import (
    LocatorCheckStatus,
    LocatorContractTest,
)


class FakeDriver:
    def __init__(
        self,
        *,
        matches=None,
        errors=None,
    ) -> None:
        self.matches = dict(
            matches or {}
        )
        self.errors = dict(
            errors or {}
        )
        self.calls = []

    def find_elements(
        self,
        by,
        value,
    ):
        locator = (by, value)

        self.calls.append(locator)

        if locator in self.errors:
            raise self.errors[locator]

        count = self.matches.get(
            locator,
            0,
        )

        return [
            object()
            for _ in range(count)
        ]


def build_registry() -> LocatorRegistry:
    return LocatorRegistry(
        (
            LocatorSpec(
                key="assistant.open",
                by=By.ID,
                value="primary",
                priority=10,
                description="Selector principal.",
            ),
            LocatorSpec(
                key="assistant.open",
                by=By.XPATH,
                value="//a[@id='fallback']",
                priority=20,
                description="Selector alternativo.",
            ),
            LocatorSpec(
                key="assistant.container",
                by=By.ID,
                value="container",
                priority=10,
            ),
        )
    )


def test_should_select_first_matching_candidate() -> None:
    driver = FakeDriver(
        matches={
            (By.ID, "primary"): 1,
            (
                By.XPATH,
                "//a[@id='fallback']",
            ): 1,
        }
    )

    contract_test = LocatorContractTest(
        driver=driver,
        registry=build_registry(),
    )

    result = contract_test.check(
        "assistant.open"
    )

    assert (
        result.status
        is LocatorCheckStatus.FOUND
    )

    assert result.selected_candidate is not None
    assert result.selected_candidate.value == "primary"
    assert result.selected_candidate.priority == 10
    assert len(result.candidates) == 2


def test_should_use_fallback_candidate() -> None:
    driver = FakeDriver(
        matches={
            (
                By.XPATH,
                "//a[@id='fallback']",
            ): 1,
        }
    )

    contract_test = LocatorContractTest(
        driver=driver,
        registry=build_registry(),
    )

    result = contract_test.check(
        "assistant.open"
    )

    assert result.found
    assert result.selected_candidate is not None

    assert (
        result.selected_candidate.value
        == "//a[@id='fallback']"
    )

    assert result.selected_candidate.priority == 20

    assert (
        result.candidates[0].status
        is LocatorCheckStatus.MISSING
    )

    assert (
        result.candidates[1].status
        is LocatorCheckStatus.FOUND
    )


def test_should_report_missing_locator() -> None:
    contract_test = LocatorContractTest(
        driver=FakeDriver(),
        registry=build_registry(),
    )

    result = contract_test.check(
        "assistant.container"
    )

    assert (
        result.status
        is LocatorCheckStatus.MISSING
    )

    assert result.selected_candidate is None
    assert result.missing
    assert result.failed


def test_should_record_candidate_error_and_continue() -> None:
    driver = FakeDriver(
        matches={
            (
                By.XPATH,
                "//a[@id='fallback']",
            ): 1,
        },
        errors={
            (
                By.ID,
                "primary",
            ): RuntimeError(
                "Selector inválido."
            ),
        },
    )

    contract_test = LocatorContractTest(
        driver=driver,
        registry=build_registry(),
    )

    result = contract_test.check(
        "assistant.open"
    )

    assert result.found

    assert (
        result.candidates[0].status
        is LocatorCheckStatus.ERROR
    )

    assert (
        "RuntimeError"
        in result.candidates[0].error
    )

    assert result.selected_candidate is not None
    assert result.selected_candidate.priority == 20


def test_should_remove_duplicate_keys_from_batch() -> None:
    driver = FakeDriver(
        matches={
            (By.ID, "container"): 1,
        }
    )

    contract_test = LocatorContractTest(
        driver=driver,
        registry=build_registry(),
    )

    results = contract_test.check_many(
        (
            "assistant.container",
            "assistant.container",
            "",
            "assistant.container",
        )
    )

    assert len(results) == 1
    assert results[0].key == "assistant.container"