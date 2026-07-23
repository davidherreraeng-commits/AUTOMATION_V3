from __future__ import annotations

import json

from pathlib import Path

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorRegistry,
    LocatorSpec,
)
from adapters.portal.gestion_transparente.locators.contract_tests import (
    LocatorContractTest,
    PortalHealthCheck,
)


class FakeDriver:
    current_url = (
        "https://portal.test/asistente"
    )
    title = "Asistente de Contratación"

    def __init__(
        self,
        matches=None,
    ) -> None:
        self.matches = dict(
            matches or {}
        )

    def find_elements(
        self,
        by,
        value,
    ):
        count = self.matches.get(
            (by, value),
            0,
        )

        return [
            object()
            for _ in range(count)
        ]


def create_health_check(
    driver: FakeDriver,
) -> PortalHealthCheck:
    registry = LocatorRegistry(
        (
            LocatorSpec(
                key="assistant.open",
                by=By.ID,
                value="assistant-open",
                priority=10,
            ),
            LocatorSpec(
                key="assistant.container",
                by=By.ID,
                value="assistant-container",
                priority=10,
            ),
        )
    )

    contract_test = LocatorContractTest(
        driver=driver,
        registry=registry,
    )

    return PortalHealthCheck(
        driver=driver,
        contract_test=contract_test,
        profile_version="v2026_07",
        required_keys={
            "assistant.open",
            "assistant.container",
        },
    )


def test_should_report_healthy_profile() -> None:
    driver = FakeDriver(
        {
            (
                By.ID,
                "assistant-open",
            ): 1,
            (
                By.ID,
                "assistant-container",
            ): 1,
        }
    )

    report = create_health_check(
        driver
    ).run()

    assert report.healthy
    assert report.total_count == 2
    assert report.found_count == 2
    assert report.missing_count == 0
    assert report.error_count == 0
    assert report.failed_keys == ()

    assert (
        report.current_url
        == "https://portal.test/asistente"
    )

    assert (
        report.page_title
        == "Asistente de Contratación"
    )


def test_should_report_missing_required_key() -> None:
    driver = FakeDriver(
        {
            (
                By.ID,
                "assistant-open",
            ): 1,
        }
    )

    report = create_health_check(
        driver
    ).run()

    assert not report.healthy
    assert report.total_count == 2
    assert report.found_count == 1
    assert report.missing_count == 1

    assert report.failed_keys == (
        "assistant.container",
    )


def test_should_write_json_report(
    tmp_path: Path,
) -> None:
    driver = FakeDriver(
        {
            (
                By.ID,
                "assistant-open",
            ): 1,
            (
                By.ID,
                "assistant-container",
            ): 1,
        }
    )

    report = create_health_check(
        driver
    ).run()

    output_path = report.write_json(
        tmp_path / "health-check.json"
    )

    assert output_path.is_file()

    payload = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert payload["profile_version"] == "v2026_07"
    assert payload["healthy"] is True
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["found"] == 2
    assert payload["failed_keys"] == []


def test_should_allow_checking_selected_keys() -> None:
    driver = FakeDriver(
        {
            (
                By.ID,
                "assistant-open",
            ): 1,
        }
    )

    report = create_health_check(
        driver
    ).run(
        keys={
            "assistant.open",
        }
    )

    assert report.healthy
    assert report.total_count == 1
    assert report.found_count == 1
    assert report.failed_keys == ()