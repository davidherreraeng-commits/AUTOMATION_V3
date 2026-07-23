from __future__ import annotations

import json

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver

from adapters.portal.gestion_transparente.locators.locator_registry import (
    LocatorRegistry,
)
from adapters.portal.gestion_transparente.locators.contract_tests.locator_contract_test import (
    LocatorContractTest,
)
from adapters.portal.gestion_transparente.locators.contract_tests.portal_health_check import (
    PortalHealthCheck,
    PortalHealthCheckReport,
)
from adapters.portal.gestion_transparente.selenium.diagnostics import (
    BrowserDiagnostics,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InteractivePhaseStatus(str, Enum):
    CHECKED = "CHECKED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class PortalHealthCheckPhase:
    """
    Define una pantalla o estado concreto del portal que debe
    posicionarse manualmente antes de comprobar sus localizadores.
    """

    name: str
    label: str
    instructions: str
    keys: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized_name = str(
            self.name
        ).strip()

        normalized_label = str(
            self.label
        ).strip()

        normalized_instructions = str(
            self.instructions
        ).strip()

        normalized_keys: list[str] = []
        seen_keys: set[str] = set()

        for key in self.keys:
            normalized_key = str(key).strip()

            if not normalized_key:
                continue

            if normalized_key in seen_keys:
                raise ValueError(
                    "La fase contiene una clave duplicada: "
                    f"{normalized_key}."
                )

            seen_keys.add(normalized_key)
            normalized_keys.append(normalized_key)

        if not normalized_name:
            raise ValueError(
                "El nombre técnico de la fase es obligatorio."
            )

        if not normalized_label:
            raise ValueError(
                "La etiqueta de la fase es obligatoria."
            )

        if not normalized_instructions:
            raise ValueError(
                "Las instrucciones de la fase son obligatorias."
            )

        if not normalized_keys:
            raise ValueError(
                "La fase debe contener al menos una clave."
            )

        object.__setattr__(
            self,
            "name",
            normalized_name,
        )

        object.__setattr__(
            self,
            "label",
            normalized_label,
        )

        object.__setattr__(
            self,
            "instructions",
            normalized_instructions,
        )

        object.__setattr__(
            self,
            "keys",
            tuple(normalized_keys),
        )


@dataclass(frozen=True, slots=True)
class PortalHealthCheckPhaseResult:
    phase: PortalHealthCheckPhase
    status: InteractivePhaseStatus
    report: PortalHealthCheckReport | None = None
    evidence: dict[str, str | None] | None = None
    diagnostics_error: str | None = None

    @property
    def checked(self) -> bool:
        return (
            self.status
            is InteractivePhaseStatus.CHECKED
        )

    @property
    def skipped(self) -> bool:
        return (
            self.status
            is InteractivePhaseStatus.SKIPPED
        )

    @property
    def healthy(self) -> bool:
        return (
            self.report is not None
            and self.report.healthy
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "phase": {
                "name": self.phase.name,
                "label": self.phase.label,
                "instructions": self.phase.instructions,
                "keys": list(self.phase.keys),
            },
            "status": self.status.value,
            "healthy": self.healthy,
            "report": (
                self.report.as_dict()
                if self.report is not None
                else None
            ),
            "evidence": self.evidence,
            "diagnostics_error": self.diagnostics_error,
        }


@dataclass(frozen=True, slots=True)
class InteractivePortalHealthCheckReport:
    profile_version: str
    started_at: datetime
    completed_at: datetime
    planned_phase_count: int
    planned_keys: tuple[str, ...]
    phases: tuple[
        PortalHealthCheckPhaseResult,
        ...
    ]
    aborted: bool = False

    @property
    def checked_phase_count(self) -> int:
        return sum(
            phase.checked
            for phase in self.phases
        )

    @property
    def skipped_phase_count(self) -> int:
        return sum(
            phase.skipped
            for phase in self.phases
        )

    @property
    def checked_reports(
        self,
    ) -> tuple[PortalHealthCheckReport, ...]:
        return tuple(
            phase.report
            for phase in self.phases
            if phase.report is not None
        )

    @property
    def total_locator_count(self) -> int:
        return sum(
            report.total_count
            for report in self.checked_reports
        )

    @property
    def found_count(self) -> int:
        return sum(
            report.found_count
            for report in self.checked_reports
        )

    @property
    def missing_count(self) -> int:
        return sum(
            report.missing_count
            for report in self.checked_reports
        )

    @property
    def error_count(self) -> int:
        return sum(
            report.error_count
            for report in self.checked_reports
        )

    @property
    def fallback_keys(self) -> tuple[str, ...]:
        keys: list[str] = []

        for report in self.checked_reports:
            keys.extend(report.fallback_keys)

        return tuple(keys)

    @property
    def failed_keys(self) -> tuple[str, ...]:
        keys: list[str] = []

        for report in self.checked_reports:
            keys.extend(report.failed_keys)

        return tuple(keys)

    @property
    def skipped_keys(self) -> tuple[str, ...]:
        keys: list[str] = []

        for phase_result in self.phases:
            if phase_result.skipped:
                keys.extend(
                    phase_result.phase.keys
                )

        return tuple(keys)

    @property
    def checked_keys(self) -> tuple[str, ...]:
        keys: list[str] = []

        for phase_result in self.phases:
            if phase_result.checked:
                keys.extend(
                    phase_result.phase.keys
                )

        return tuple(keys)

    @property
    def unprocessed_keys(self) -> tuple[str, ...]:
        processed = {
            *self.checked_keys,
            *self.skipped_keys,
        }

        return tuple(
            key
            for key in self.planned_keys
            if key not in processed
        )

    @property
    def complete(self) -> bool:
        return (
            not self.aborted
            and len(self.phases)
            == self.planned_phase_count
            and self.skipped_phase_count == 0
            and not self.unprocessed_keys
        )

    @property
    def healthy(self) -> bool:
        reports = self.checked_reports

        return (
            self.complete
            and bool(reports)
            and all(
                report.healthy
                for report in reports
            )
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "profile_version": self.profile_version,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "aborted": self.aborted,
            "complete": self.complete,
            "healthy": self.healthy,
            "summary": {
                "planned_phases": (
                    self.planned_phase_count
                ),
                "processed_phases": len(
                    self.phases
                ),
                "checked_phases": (
                    self.checked_phase_count
                ),
                "skipped_phases": (
                    self.skipped_phase_count
                ),
                "planned_locators": len(
                    self.planned_keys
                ),
                "checked_locators": (
                    self.total_locator_count
                ),
                "found": self.found_count,
                "missing": self.missing_count,
                "errors": self.error_count,
                "fallbacks": len(
                    self.fallback_keys
                ),
            },
            "failed_keys": list(
                self.failed_keys
            ),
            "fallback_keys": list(
                self.fallback_keys
            ),
            "skipped_keys": list(
                self.skipped_keys
            ),
            "unprocessed_keys": list(
                self.unprocessed_keys
            ),
            "phases": [
                phase.as_dict()
                for phase in self.phases
            ],
        }

    def write_json(
        self,
        path: str | Path,
    ) -> Path:
        output_path = Path(path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            json.dumps(
                self.as_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        return output_path


InputReader = Callable[[str], str]
OutputWriter = Callable[[str], None]


class InteractivePortalHealthCheckRunner:
    """
    Ejecuta el plan interactivo de validación.

    Controles disponibles:

    - Enter o R: ejecutar la fase.
    - S: omitir la fase.
    - Q: finalizar el diagnóstico.
    """

    def __init__(
        self,
        *,
        driver: WebDriver,
        registry: LocatorRegistry,
        profile_version: str,
        phases: Sequence[
            PortalHealthCheckPhase
        ],
        input_reader: InputReader = input,
        output_writer: OutputWriter = print,
        diagnostics: BrowserDiagnostics | None = None,
        capture_failed_evidence: bool = True,
        require_complete_coverage: bool = True,
    ) -> None:
        normalized_version = str(
            profile_version
        ).strip()

        normalized_phases = tuple(phases)

        if not normalized_version:
            raise ValueError(
                "La versión del perfil es obligatoria."
            )

        if not normalized_phases:
            raise ValueError(
                "El plan debe contener al menos una fase."
            )

        self._validate_plan(
            registry=registry,
            phases=normalized_phases,
            require_complete_coverage=(
                require_complete_coverage
            ),
        )

        planned_keys = tuple(
            key
            for phase in normalized_phases
            for key in phase.keys
        )

        self._driver = driver
        self._registry = registry
        self._profile_version = normalized_version
        self._phases = normalized_phases
        self._planned_keys = planned_keys
        self._input_reader = input_reader
        self._output_writer = output_writer
        self._diagnostics = diagnostics
        self._capture_failed_evidence = (
            capture_failed_evidence
        )

        contract_test = LocatorContractTest(
            driver=driver,
            registry=registry,
        )

        self._health_check = PortalHealthCheck(
            driver=driver,
            contract_test=contract_test,
            profile_version=normalized_version,
            required_keys=planned_keys,
        )

    @property
    def phases(
        self,
    ) -> tuple[PortalHealthCheckPhase, ...]:
        return self._phases

    def run(
        self,
    ) -> InteractivePortalHealthCheckReport:
        started_at = utc_now()

        phase_results: list[
            PortalHealthCheckPhaseResult
        ] = []

        aborted = False

        self._write_header()

        for index, phase in enumerate(
            self._phases,
            start=1,
        ):
            self._write_phase_header(
                index=index,
                phase=phase,
            )

            action = self._read_action()

            if action == "q":
                aborted = True

                self._output_writer(
                    "Diagnóstico finalizado por el usuario."
                )
                break

            if action == "s":
                phase_results.append(
                    PortalHealthCheckPhaseResult(
                        phase=phase,
                        status=(
                            InteractivePhaseStatus.SKIPPED
                        ),
                    )
                )

                self._output_writer(
                    f"Fase omitida: {phase.label}"
                )
                continue

            report = self._health_check.run(
                keys=phase.keys
            )

            evidence: dict[
                str,
                str | None,
            ] | None = None

            diagnostics_error: str | None = None

            if (
                not report.healthy
                and self._capture_failed_evidence
                and self._diagnostics is not None
            ):
                try:
                    captured = (
                        self._diagnostics.capture(
                            event=(
                                "health_check_"
                                f"{phase.name}"
                            ),
                            metadata={
                                "phase": phase.name,
                                "profile_version": (
                                    self._profile_version
                                ),
                                "failed_keys": list(
                                    report.failed_keys
                                ),
                            },
                        )
                    )

                    evidence = (
                        captured.as_metadata()
                    )

                except Exception as error:
                    diagnostics_error = (
                        f"{type(error).__name__}: "
                        f"{error}"
                    )

            phase_result = (
                PortalHealthCheckPhaseResult(
                    phase=phase,
                    status=(
                        InteractivePhaseStatus.CHECKED
                    ),
                    report=report,
                    evidence=evidence,
                    diagnostics_error=(
                        diagnostics_error
                    ),
                )
            )

            phase_results.append(
                phase_result
            )

            self._write_phase_summary(
                phase_result
            )

        completed_at = utc_now()

        return InteractivePortalHealthCheckReport(
            profile_version=self._profile_version,
            started_at=started_at,
            completed_at=completed_at,
            planned_phase_count=len(
                self._phases
            ),
            planned_keys=self._planned_keys,
            phases=tuple(
                phase_results
            ),
            aborted=aborted,
        )

    def _read_action(self) -> str:
        while True:
            raw_action = self._input_reader(
                "Presiona Enter para comprobar, "
                "[S] omitir o [Q] finalizar: "
            )

            action = str(
                raw_action
            ).strip().lower()

            if action in {
                "",
                "r",
                "s",
                "q",
            }:
                return action or "r"

            self._output_writer(
                "Opción inválida. Usa Enter, R, S o Q."
            )

    def _write_header(self) -> None:
        self._output_writer("")
        self._output_writer(
            "=== Gestión Transparente: "
            "verificación interactiva ==="
        )
        self._output_writer(
            "Perfil: "
            f"{self._profile_version}"
        )
        self._output_writer(
            "Fases: "
            f"{len(self._phases)}"
        )
        self._output_writer(
            "Localizadores planificados: "
            f"{len(self._planned_keys)}"
        )
        self._output_writer("")

    def _write_phase_header(
        self,
        *,
        index: int,
        phase: PortalHealthCheckPhase,
    ) -> None:
        self._output_writer("")
        self._output_writer(
            f"[{index}/{len(self._phases)}] "
            f"{phase.label}"
        )
        self._output_writer(
            phase.instructions
        )
        self._output_writer(
            "Claves a comprobar:"
        )

        for key in phase.keys:
            self._output_writer(
                f"  - {key}"
            )

    def _write_phase_summary(
        self,
        phase_result: PortalHealthCheckPhaseResult,
    ) -> None:
        report = phase_result.report

        if report is None:
            return

        self._output_writer(
            "Resultado: "
            f"{report.found_count} encontrados, "
            f"{report.missing_count} ausentes, "
            f"{report.error_count} con error."
        )

        if report.fallback_keys:
            self._output_writer(
                "Resueltos mediante fallback:"
            )

            for key in report.fallback_keys:
                self._output_writer(
                    f"  - {key}"
                )

        if report.failed_keys:
            self._output_writer(
                "Claves no resueltas:"
            )

            for key in report.failed_keys:
                self._output_writer(
                    f"  - {key}"
                )

        if phase_result.evidence is not None:
            self._output_writer(
                "Se capturó evidencia de diagnóstico."
            )

    @staticmethod
    def _validate_plan(
        *,
        registry: LocatorRegistry,
        phases: tuple[
            PortalHealthCheckPhase,
            ...
        ],
        require_complete_coverage: bool,
    ) -> None:
        phase_names: set[str] = set()
        planned_keys: set[str] = set()

        for phase in phases:
            if phase.name in phase_names:
                raise ValueError(
                    "El plan contiene un nombre de fase "
                    f"duplicado: {phase.name}."
                )

            phase_names.add(phase.name)

            for key in phase.keys:
                if key in planned_keys:
                    raise ValueError(
                        "El localizador aparece en más de una "
                        f"fase: {key}."
                    )

                planned_keys.add(key)

        available_keys = set(
            registry.keys()
        )

        unknown_keys = (
            planned_keys
            - available_keys
        )

        if unknown_keys:
            raise ValueError(
                "El plan contiene claves que no existen "
                "en el registro: "
                + ", ".join(
                    sorted(unknown_keys)
                )
                + "."
            )

        if require_complete_coverage:
            uncovered_keys = (
                available_keys
                - planned_keys
            )

            if uncovered_keys:
                raise ValueError(
                    "El plan no cubre todos los localizadores "
                    "del registro. Faltan: "
                    + ", ".join(
                        sorted(uncovered_keys)
                    )
                    + "."
                )