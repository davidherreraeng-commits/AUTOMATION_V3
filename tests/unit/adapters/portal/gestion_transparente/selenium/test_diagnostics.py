<<<<<<< HEAD
from __future__ import annotations

import json

from pathlib import Path

from adapters.portal.gestion_transparente.selenium.diagnostics import (
    BrowserDiagnostics,
)


class FakeDriver:
    current_url = (
        "https://portal.test/asistente"
    )
    title = "Asistente de Contratación"
    page_source = (
        "<html><body>Portal</body></html>"
    )

    def save_screenshot(
        self,
        path: str,
    ) -> bool:
        Path(path).write_bytes(
            b"fake-png"
        )

        return True


class ScreenshotFailingDriver(FakeDriver):
    def save_screenshot(
        self,
        path: str,
    ) -> bool:
        raise RuntimeError(
            "No fue posible capturar."
        )


def test_should_capture_browser_evidence(
    tmp_path: Path,
) -> None:
    diagnostics = BrowserDiagnostics(
        FakeDriver(),
        tmp_path,
    )

    evidence = diagnostics.capture(
        event="locator_failure",
        metadata={
            "locator_key": "assistant.open",
        },
    )

    assert evidence.directory.is_dir()
    assert evidence.metadata_path.is_file()

    assert evidence.screenshot_path is not None
    assert evidence.screenshot_path.is_file()

    assert evidence.page_source_path is not None
    assert evidence.page_source_path.is_file()

    metadata = json.loads(
        evidence.metadata_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        metadata["current_url"]
        == "https://portal.test/asistente"
    )

    assert (
        metadata["metadata"]["locator_key"]
        == "assistant.open"
    )


def test_should_preserve_metadata_when_screenshot_fails(
    tmp_path: Path,
) -> None:
    diagnostics = BrowserDiagnostics(
        ScreenshotFailingDriver(),
        tmp_path,
    )

    evidence = diagnostics.capture(
        event="failed screenshot"
    )

    assert evidence.screenshot_path is None
    assert evidence.metadata_path.is_file()

    metadata = json.loads(
        evidence.metadata_path.read_text(
            encoding="utf-8"
        )
    )

    assert metadata["capture_errors"]

    assert "Error capturando pantalla" in (
        metadata["capture_errors"][0]
    )


def test_should_sanitize_diagnostic_directory_name(
    tmp_path: Path,
) -> None:
    diagnostics = BrowserDiagnostics(
        FakeDriver(),
        tmp_path,
    )

    evidence = diagnostics.capture(
        event="locator: assistant.open / visible"
    )

    assert ":" not in evidence.directory.name
    assert "/" not in evidence.directory.name
=======
from __future__ import annotations

import json

from pathlib import Path

from adapters.portal.gestion_transparente.selenium.diagnostics import (
    BrowserDiagnostics,
)


class FakeDriver:
    current_url = (
        "https://portal.test/asistente"
    )
    title = "Asistente de Contratación"
    page_source = (
        "<html><body>Portal</body></html>"
    )

    def save_screenshot(
        self,
        path: str,
    ) -> bool:
        Path(path).write_bytes(
            b"fake-png"
        )

        return True


class ScreenshotFailingDriver(FakeDriver):
    def save_screenshot(
        self,
        path: str,
    ) -> bool:
        raise RuntimeError(
            "No fue posible capturar."
        )


def test_should_capture_browser_evidence(
    tmp_path: Path,
) -> None:
    diagnostics = BrowserDiagnostics(
        FakeDriver(),
        tmp_path,
    )

    evidence = diagnostics.capture(
        event="locator_failure",
        metadata={
            "locator_key": "assistant.open",
        },
    )

    assert evidence.directory.is_dir()
    assert evidence.metadata_path.is_file()

    assert evidence.screenshot_path is not None
    assert evidence.screenshot_path.is_file()

    assert evidence.page_source_path is not None
    assert evidence.page_source_path.is_file()

    metadata = json.loads(
        evidence.metadata_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        metadata["current_url"]
        == "https://portal.test/asistente"
    )

    assert (
        metadata["metadata"]["locator_key"]
        == "assistant.open"
    )


def test_should_preserve_metadata_when_screenshot_fails(
    tmp_path: Path,
) -> None:
    diagnostics = BrowserDiagnostics(
        ScreenshotFailingDriver(),
        tmp_path,
    )

    evidence = diagnostics.capture(
        event="failed screenshot"
    )

    assert evidence.screenshot_path is None
    assert evidence.metadata_path.is_file()

    metadata = json.loads(
        evidence.metadata_path.read_text(
            encoding="utf-8"
        )
    )

    assert metadata["capture_errors"]

    assert "Error capturando pantalla" in (
        metadata["capture_errors"][0]
    )


def test_should_sanitize_diagnostic_directory_name(
    tmp_path: Path,
) -> None:
    diagnostics = BrowserDiagnostics(
        FakeDriver(),
        tmp_path,
    )

    evidence = diagnostics.capture(
        event="locator: assistant.open / visible"
    )

    assert ":" not in evidence.directory.name
    assert "/" not in evidence.directory.name
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
    assert " " not in evidence.directory.name