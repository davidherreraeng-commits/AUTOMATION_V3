from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from selenium.webdriver.remote.webdriver import WebDriver

from adapters.portal.gestion_transparente.locators.locator_registry import (
    LocatorRegistry,
)


class LocatorCheckStatus(str, Enum):
    """
    Resultado de comprobar una clave semántica contra el DOM actual.
    """

    FOUND = "FOUND"
    MISSING = "MISSING"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class LocatorCandidateCheck:
    """
    Resultado individual de un candidato de localización.
    """

    key: str
    by: str
    value: str
    priority: int
    description: str | None
    status: LocatorCheckStatus
    match_count: int
    error: str | None = None

    @property
    def found(self) -> bool:
        return self.status is LocatorCheckStatus.FOUND

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "by": self.by,
            "value": self.value,
            "priority": self.priority,
            "description": self.description,
            "status": self.status.value,
            "match_count": self.match_count,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class LocatorContractResult:
    """
    Resultado contractual de una clave semántica.

    Puede contener varios candidatos porque una clave puede tener un
    selector principal y uno o más fallbacks.
    """

    key: str
    status: LocatorCheckStatus
    candidates: tuple[LocatorCandidateCheck, ...]
    selected_candidate: LocatorCandidateCheck | None = None

    @property
    def found(self) -> bool:
        return self.status is LocatorCheckStatus.FOUND

    @property
    def missing(self) -> bool:
        return self.status is LocatorCheckStatus.MISSING

    @property
    def failed(self) -> bool:
        return self.status is not LocatorCheckStatus.FOUND

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "status": self.status.value,
            "found": self.found,
            "selected_candidate": (
                self.selected_candidate.as_dict()
                if self.selected_candidate is not None
                else None
            ),
            "candidates": [
                candidate.as_dict()
                for candidate in self.candidates
            ],
        }


class LocatorContractTest:
    """
    Comprueba un registro de localizadores contra el DOM actual.

    Esta clase no modifica la página. Únicamente utiliza find_elements()
    para determinar:

    - Si el selector principal funciona.
    - Si fue necesario utilizar un fallback.
    - Cuántos elementos coinciden.
    - Si Selenium produjo un error evaluando el selector.
    """

    def __init__(
        self,
        *,
        driver: WebDriver,
        registry: LocatorRegistry,
    ) -> None:
        self._driver = driver
        self._registry = registry

    @property
    def available_keys(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._registry.keys())
        )

    def check(
        self,
        key: str,
    ) -> LocatorContractResult:
        """
        Comprueba todos los candidatos registrados para una clave.

        El primer candidato encontrado según prioridad se considera
        el candidato seleccionado.
        """

        normalized_key = str(key).strip()

        if not normalized_key:
            raise ValueError(
                "La clave del localizador es obligatoria."
            )

        candidates = self._registry.candidates(
            normalized_key
        )

        checks: list[LocatorCandidateCheck] = []
        selected_candidate: LocatorCandidateCheck | None = None

        for candidate in candidates:
            try:
                elements = self._driver.find_elements(
                    candidate.by,
                    candidate.value,
                )

                match_count = len(elements)

                status = (
                    LocatorCheckStatus.FOUND
                    if match_count > 0
                    else LocatorCheckStatus.MISSING
                )

                check = LocatorCandidateCheck(
                    key=candidate.key,
                    by=candidate.by,
                    value=candidate.value,
                    priority=candidate.priority,
                    description=candidate.description,
                    status=status,
                    match_count=match_count,
                    error=None,
                )

            except Exception as error:
                check = LocatorCandidateCheck(
                    key=candidate.key,
                    by=candidate.by,
                    value=candidate.value,
                    priority=candidate.priority,
                    description=candidate.description,
                    status=LocatorCheckStatus.ERROR,
                    match_count=0,
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )

            checks.append(check)

            if (
                selected_candidate is None
                and check.found
            ):
                selected_candidate = check

        if selected_candidate is not None:
            overall_status = LocatorCheckStatus.FOUND

        elif checks and all(
            check.status is LocatorCheckStatus.ERROR
            for check in checks
        ):
            overall_status = LocatorCheckStatus.ERROR

        else:
            overall_status = LocatorCheckStatus.MISSING

        return LocatorContractResult(
            key=normalized_key,
            status=overall_status,
            candidates=tuple(checks),
            selected_candidate=selected_candidate,
        )

    def check_many(
        self,
        keys: Iterable[str],
    ) -> tuple[LocatorContractResult, ...]:
        """
        Comprueba varias claves eliminando duplicados y conservando
        el orden recibido.
        """

        normalized_keys: list[str] = []
        seen: set[str] = set()

        for key in keys:
            normalized_key = str(key).strip()

            if not normalized_key:
                continue

            if normalized_key in seen:
                continue

            seen.add(normalized_key)
            normalized_keys.append(normalized_key)

        return tuple(
            self.check(key)
            for key in normalized_keys
        )

    def check_all(
        self,
    ) -> tuple[LocatorContractResult, ...]:
        """
        Comprueba todas las claves del registro.
        """

        return self.check_many(
            self.available_keys
        )