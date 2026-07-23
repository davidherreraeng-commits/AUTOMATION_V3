from __future__ import annotations

import json

from pathlib import Path

import pytest

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorRegistry,
    LocatorSpec,
)
from adapters.portal.gestion_transparente.locators.contract_tests import (
    InteractivePortalHealthCheckRunner,
    PortalHealthCheckPhase,
)


class FakeDriver:
    current_url = (
        "https://portal.test/current"
    )
    title = "Gestión Transparente"

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


class FakeEvidence:
    def as_metadata(self):
        return {
            "directory": "evidence/test",
            "metadata_path": (
                "evidence/test/metadata.json"
            ),
            "screenshot_path": (
                "evidence/test/screenshot.png"
            ),
            "page_source_path": (
                "evidence/test/page_source.html"
            ),
        }


class FakeDiagnostics:
    def __init__(self) -> None:
        self.calls = []

    def capture(
        self,
        *,
        event,
        metadata=None,
        error=None,
    ):
        self.calls.append(
            {
                "event": event,
                "metadata": metadata,
                "error": error,
            }
        )

        return FakeEvidence()


def build_registry() -> LocatorRegistry:
    return LocatorRegistry(
        (
            LocatorSpec(
                key="phase.one",
                by=By.ID,
                value="phase-one",
            ),
            LocatorSpec(
                key="phase.two",
                by=By.ID,
                value="phase-two",
            ),
        )
    )


def build_phases():
    return (
        PortalHealthCheckPhase(
            name="first",
            label="Primera fase",
            instructions=(
                "Ubica la primera pantalla."
            ),
            keys=(
                "phase.one",
            ),
        ),
        PortalHealthCheckPhase(
            name="second",
            label="Segunda fase",
            instructions=(
                "Ubica la segunda pantalla."
            ),
            keys=(
                "phase.two",
            ),
        ),
    )


def input_sequence(
    responses,
):
    iterator = iter(responses)

    return lambda _: next(iterator)


def test_should_run_complete_healthy_plan() -> None:
    driver = FakeDriver(
        matches={
            (
                By.ID,
                "phase-one",
            ): 1,
            (
                By.ID,
                "phase-two",
            ): 1,
        }
    )

    runner = (
        InteractivePortalHealthCheckRunner(
            driver=driver,
            registry=build_registry(),
            profile_version="test",
            phases=build_phases(),
            input_reader=input_sequence(
                (
                    "",
                    "r",
                )
            ),
            output_writer=lambda _: None,
        )
    )

    report = runner.run()

    assert report.complete
    assert report.healthy
    assert not report.aborted
    assert report.checked_phase_count == 2
    assert report.skipped_phase_count == 0
    assert report.found_count == 2
    assert report.failed_keys == ()
    assert report.unprocessed_keys == ()


def test_should_mark_skipped_phase_as_incomplete() -> None:
    driver = FakeDriver(
        matches={
            (
                By.ID,
                "phase-one",
            ): 1,
        }
    )

    runner = (
        InteractivePortalHealthCheckRunner(
            driver=driver,
            registry=build_registry(),
            profile_version="test",
            phases=build_phases(),
            input_reader=input_sequence(
                (
                    "",
                    "s",
                )
            ),
            output_writer=lambda _: None,
        )
    )

    report = runner.run()

    assert not report.complete
    assert not report.healthy
    assert report.checked_phase_count == 1
    assert report.skipped_phase_count == 1

    assert report.skipped_keys == (
        "phase.two",
    )


def test_should_abort_and_report_unprocessed_keys() -> None:
    runner = (
        InteractivePortalHealthCheckRunner(
            driver=FakeDriver(),
            registry=build_registry(),
            profile_version="test",
            phases=build_phases(),
            input_reader=input_sequence(
                (
                    "q",
                )
            ),
            output_writer=lambda _: None,
        )
    )

    report = runner.run()

    assert report.aborted
    assert not report.complete
    assert not report.healthy
    assert report.phases == ()

    assert report.unprocessed_keys == (
        "phase.one",
        "phase.two",
    )


def test_should_capture_evidence_for_failed_phase() -> None:
    diagnostics = FakeDiagnostics()

    runner = (
        InteractivePortalHealthCheckRunner(
            driver=FakeDriver(),
            registry=build_registry(),
            profile_version="test",
            phases=build_phases(),
            input_reader=input_sequence(
                (
                    "",
                    "s",
                )
            ),
            output_writer=lambda _: None,
            diagnostics=diagnostics,
            capture_failed_evidence=True,
        )
    )

    report = runner.run()

    assert len(diagnostics.calls) == 1

    first_phase = report.phases[0]

    assert first_phase.evidence is not None

    assert (
        first_phase.evidence["directory"]
        == "evidence/test"
    )


def test_should_reject_locator_in_multiple_phases() -> None:
    duplicated_phases = (
        PortalHealthCheckPhase(
            name="first",
            label="Primera",
            instructions="Primera fase.",
            keys=(
                "phase.one",
            ),
        ),
        PortalHealthCheckPhase(
            name="second",
            label="Segunda",
            instructions="Segunda fase.",
            keys=(
                "phase.one",
                "phase.two",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="más de una fase",
    ):
        InteractivePortalHealthCheckRunner(
            driver=FakeDriver(),
            registry=build_registry(),
            profile_version="test",
            phases=duplicated_phases,
            output_writer=lambda _: None,
        )


def test_should_write_interactive_json_report(
    tmp_path: Path,
) -> None:
    driver = FakeDriver(
        matches={
            (
                By.ID,
                "phase-one",
            ): 1,
            (
                By.ID,
                "phase-two",
            ): 1,
        }
    )

    runner = (
        InteractivePortalHealthCheckRunner(
            driver=driver,
            registry=build_registry(),
            profile_version="test",
            phases=build_phases(),
            input_reader=input_sequence(
                (
                    "",
                    "",
                )
            ),
            output_writer=lambda _: None,
        )
    )

    report = runner.run()

    output_path = report.write_json(
        tmp_path / "interactive.json"
    )

    payload = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert payload["healthy"] is True
    assert payload["complete"] is True

    assert (
        payload["summary"]["planned_locators"]
        == 2
    )

    assert (
        payload["summary"]["found"]
        == 2
    )