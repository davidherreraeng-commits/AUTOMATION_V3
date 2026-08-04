from __future__ import annotations

import json
import re

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from selenium.webdriver.remote.webdriver import WebDriver


class DiagnosticsCaptureError(RuntimeError):
    """No fue posible crear la evidencia de diagnóstico."""


@dataclass(frozen=True, slots=True)
class DiagnosticEvidence:
    directory: Path
    metadata_path: Path
    screenshot_path: Path | None = None
    page_source_path: Path | None = None

    def as_metadata(self) -> dict[str, str | None]:
        return {
            "directory": str(self.directory),
            "metadata_path": str(
                self.metadata_path
            ),
            "screenshot_path": (
                str(self.screenshot_path)
                if self.screenshot_path is not None
                else None
            ),
            "page_source_path": (
                str(self.page_source_path)
                if self.page_source_path is not None
                else None
            ),
        }


class BrowserDiagnostics:
    """
    Captura evidencia del navegador ante un fallo.

    Genera:

    - Captura de pantalla.
    - Código HTML.
    - Metadatos JSON.
    - URL y título actuales.
    - Información del error.
    """

    def __init__(
        self,
        driver: WebDriver,
        output_directory: str | Path,
    ) -> None:
        self._driver = driver
        self._output_directory = Path(
            output_directory
        )

    @property
    def output_directory(self) -> Path:
        return self._output_directory

    def capture(
        self,
        *,
        event: str,
        metadata: Mapping[str, Any] | None = None,
        error: BaseException | None = None,
    ) -> DiagnosticEvidence:
        timestamp = datetime.now(
            timezone.utc
        )

        event_slug = self._sanitize_name(
            event
        )

        directory_name = (
            timestamp.strftime(
                "%Y%m%dT%H%M%S_%fZ"
            )
            + "_"
            + event_slug
            + "_"
            + uuid4().hex[:8]
        )

        directory = (
            self._output_directory
            / directory_name
        )

        try:
            directory.mkdir(
                parents=True,
                exist_ok=False,
            )
        except OSError as capture_error:
            raise DiagnosticsCaptureError(
                "No fue posible crear el directorio "
                f"de diagnóstico '{directory}': "
                f"{capture_error}"
            ) from capture_error

        capture_errors: list[str] = []

        screenshot_path = (
            directory / "screenshot.png"
        )

        try:
            screenshot_created = bool(
                self._driver.save_screenshot(
                    str(screenshot_path)
                )
            )

            if not screenshot_created:
                capture_errors.append(
                    "WebDriver devolvió False al capturar "
                    "la pantalla."
                )
                screenshot_path = None

        except Exception as screenshot_error:
            capture_errors.append(
                "Error capturando pantalla: "
                f"{type(screenshot_error).__name__}: "
                f"{screenshot_error}"
            )
            screenshot_path = None

        page_source_path = (
            directory / "page_source.html"
        )

        try:
            page_source = (
                self._driver.page_source
            )

            page_source_path.write_text(
                str(page_source),
                encoding="utf-8",
            )

        except Exception as source_error:
            capture_errors.append(
                "Error capturando HTML: "
                f"{type(source_error).__name__}: "
                f"{source_error}"
            )
            page_source_path = None

        current_url = self._safe_driver_value(
            "current_url",
            capture_errors,
        )

        title = self._safe_driver_value(
            "title",
            capture_errors,
        )

        metadata_path = (
            directory / "metadata.json"
        )

        diagnostic_metadata = {
            "event": str(event),
            "captured_at": (
                timestamp.isoformat()
            ),
            "current_url": current_url,
            "title": title,
            "error_type": (
                type(error).__name__
                if error is not None
                else None
            ),
            "error_message": (
                str(error)
                if error is not None
                else None
            ),
            "metadata": dict(
                metadata or {}
            ),
            "capture_errors": capture_errors,
        }

        try:
            metadata_path.write_text(
                json.dumps(
                    diagnostic_metadata,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                    default=str,
                ),
                encoding="utf-8",
            )
        except OSError as metadata_error:
            raise DiagnosticsCaptureError(
                "No fue posible escribir los metadatos "
                f"del diagnóstico: {metadata_error}"
            ) from metadata_error

        return DiagnosticEvidence(
            directory=directory,
            metadata_path=metadata_path,
            screenshot_path=screenshot_path,
            page_source_path=page_source_path,
        )

    def _safe_driver_value(
        self,
        attribute: str,
        capture_errors: list[str],
    ) -> Any:
        try:
            return getattr(
                self._driver,
                attribute,
            )

        except Exception as driver_error:
            capture_errors.append(
                f"Error obteniendo {attribute}: "
                f"{type(driver_error).__name__}: "
                f"{driver_error}"
            )
            return None

    @staticmethod
    def _sanitize_name(
        value: str,
    ) -> str:
        normalized = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            str(value).strip(),
        ).strip("_")

        return normalized or "diagnostic"