<<<<<<< HEAD
from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from selenium.webdriver.remote.webdriver import WebDriver

from adapters.portal.gestion_transparente.locators.contract_tests.locator_contract_test import (
    LocatorCheckStatus,
    LocatorContractResult,
    LocatorContractTest,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class PortalHealthCheckReport:
    """
    Informe completo de compatibilidad entre un perfil versionado
    y el DOM actual del portal.
    """

    profile_version: str
    started_at: datetime
    completed_at: datetime
    current_url: str | None
    page_title: str | None
    checks: tuple[LocatorContractResult, ...]

    @property
    def total_count(self) -> int:
        return len(self.checks)

    @property
    def found_count(self) -> int:
        return sum(
            check.status is LocatorCheckStatus.FOUND
            for check in self.checks
        )

    @property
    def missing_count(self) -> int:
        return sum(
            check.status is LocatorCheckStatus.MISSING
            for check in self.checks
        )

    @property
    def error_count(self) -> int:
        return sum(
            check.status is LocatorCheckStatus.ERROR
            for check in self.checks
        )

    @property
    def healthy(self) -> bool:
        return (
            self.total_count > 0
            and self.found_count == self.total_count
        )

    @property
    def failed_keys(self) -> tuple[str, ...]:
        return tuple(
            check.key
            for check in self.checks
            if check.failed
        )

    @property
    def fallback_keys(self) -> tuple[str, ...]:
        """
        Claves encontradas mediante un candidato diferente al de mayor
        prioridad.
        """

        fallback_keys: list[str] = []

        for check in self.checks:
            selected = check.selected_candidate

            if selected is None:
                continue

            candidates = check.candidates

            if not candidates:
                continue

            primary_priority = min(
                candidate.priority
                for candidate in candidates
            )

            if selected.priority > primary_priority:
                fallback_keys.append(
                    check.key
                )

        return tuple(fallback_keys)

    def as_dict(self) -> dict[str, object]:
        return {
            "profile_version": self.profile_version,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "current_url": self.current_url,
            "page_title": self.page_title,
            "healthy": self.healthy,
            "summary": {
                "total": self.total_count,
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
            "checks": [
                check.as_dict()
                for check in self.checks
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


class PortalHealthCheck:
    """
    Ejecuta una prueba de salud para un perfil de localizadores.
    """

    def __init__(
        self,
        *,
        driver: WebDriver,
        contract_test: LocatorContractTest,
        profile_version: str,
        required_keys: Iterable[str],
    ) -> None:
        normalized_version = str(
            profile_version
        ).strip()

        if not normalized_version:
            raise ValueError(
                "La versión del perfil es obligatoria."
            )

        normalized_required_keys = tuple(
            sorted(
                {
                    str(key).strip()
                    for key in required_keys
                    if str(key).strip()
                }
            )
        )

        if not normalized_required_keys:
            raise ValueError(
                "Debe existir al menos una clave obligatoria."
            )

        self._driver = driver
        self._contract_test = contract_test
        self._profile_version = normalized_version
        self._required_keys = normalized_required_keys

    @property
    def required_keys(self) -> tuple[str, ...]:
        return self._required_keys

    def run(
        self,
        keys: Iterable[str] | None = None,
    ) -> PortalHealthCheckReport:
        started_at = utc_now()

        selected_keys = (
            self._required_keys
            if keys is None
            else tuple(keys)
        )

        checks = self._contract_test.check_many(
            selected_keys
        )

        completed_at = utc_now()

        return PortalHealthCheckReport(
            profile_version=self._profile_version,
            started_at=started_at,
            completed_at=completed_at,
            current_url=self._safe_driver_value(
                "current_url"
            ),
            page_title=self._safe_driver_value(
                "title"
            ),
            checks=checks,
        )

    def _safe_driver_value(
        self,
        attribute: str,
    ) -> str | None:
        try:
            value = getattr(
                self._driver,
                attribute,
            )

        except Exception:
            return None

        if value is None:
            return None

        normalized_value = str(value).strip()

=======
from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from selenium.webdriver.remote.webdriver import WebDriver

from adapters.portal.gestion_transparente.locators.contract_tests.locator_contract_test import (
    LocatorCheckStatus,
    LocatorContractResult,
    LocatorContractTest,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class PortalHealthCheckReport:
    """
    Informe completo de compatibilidad entre un perfil versionado
    y el DOM actual del portal.
    """

    profile_version: str
    started_at: datetime
    completed_at: datetime
    current_url: str | None
    page_title: str | None
    checks: tuple[LocatorContractResult, ...]

    @property
    def total_count(self) -> int:
        return len(self.checks)

    @property
    def found_count(self) -> int:
        return sum(
            check.status is LocatorCheckStatus.FOUND
            for check in self.checks
        )

    @property
    def missing_count(self) -> int:
        return sum(
            check.status is LocatorCheckStatus.MISSING
            for check in self.checks
        )

    @property
    def error_count(self) -> int:
        return sum(
            check.status is LocatorCheckStatus.ERROR
            for check in self.checks
        )

    @property
    def healthy(self) -> bool:
        return (
            self.total_count > 0
            and self.found_count == self.total_count
        )

    @property
    def failed_keys(self) -> tuple[str, ...]:
        return tuple(
            check.key
            for check in self.checks
            if check.failed
        )

    @property
    def fallback_keys(self) -> tuple[str, ...]:
        """
        Claves encontradas mediante un candidato diferente al de mayor
        prioridad.
        """

        fallback_keys: list[str] = []

        for check in self.checks:
            selected = check.selected_candidate

            if selected is None:
                continue

            candidates = check.candidates

            if not candidates:
                continue

            primary_priority = min(
                candidate.priority
                for candidate in candidates
            )

            if selected.priority > primary_priority:
                fallback_keys.append(
                    check.key
                )

        return tuple(fallback_keys)

    def as_dict(self) -> dict[str, object]:
        return {
            "profile_version": self.profile_version,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "current_url": self.current_url,
            "page_title": self.page_title,
            "healthy": self.healthy,
            "summary": {
                "total": self.total_count,
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
            "checks": [
                check.as_dict()
                for check in self.checks
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


class PortalHealthCheck:
    """
    Ejecuta una prueba de salud para un perfil de localizadores.
    """

    def __init__(
        self,
        *,
        driver: WebDriver,
        contract_test: LocatorContractTest,
        profile_version: str,
        required_keys: Iterable[str],
    ) -> None:
        normalized_version = str(
            profile_version
        ).strip()

        if not normalized_version:
            raise ValueError(
                "La versión del perfil es obligatoria."
            )

        normalized_required_keys = tuple(
            sorted(
                {
                    str(key).strip()
                    for key in required_keys
                    if str(key).strip()
                }
            )
        )

        if not normalized_required_keys:
            raise ValueError(
                "Debe existir al menos una clave obligatoria."
            )

        self._driver = driver
        self._contract_test = contract_test
        self._profile_version = normalized_version
        self._required_keys = normalized_required_keys

    @property
    def required_keys(self) -> tuple[str, ...]:
        return self._required_keys

    def run(
        self,
        keys: Iterable[str] | None = None,
    ) -> PortalHealthCheckReport:
        started_at = utc_now()

        selected_keys = (
            self._required_keys
            if keys is None
            else tuple(keys)
        )

        checks = self._contract_test.check_many(
            selected_keys
        )

        completed_at = utc_now()

        return PortalHealthCheckReport(
            profile_version=self._profile_version,
            started_at=started_at,
            completed_at=completed_at,
            current_url=self._safe_driver_value(
                "current_url"
            ),
            page_title=self._safe_driver_value(
                "title"
            ),
            checks=checks,
        )

    def _safe_driver_value(
        self,
        attribute: str,
    ) -> str | None:
        try:
            value = getattr(
                self._driver,
                attribute,
            )

        except Exception:
            return None

        if value is None:
            return None

        normalized_value = str(value).strip()

>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        return normalized_value or None