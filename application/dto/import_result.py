from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from domain.models import ContractData


@dataclass(frozen=True, slots=True)
class ImportIssue:
    """
    Problema detectado al importar una fila.

    El código permite clasificar el problema sin depender del texto
    presentado posteriormente al usuario.
    """

    code: str
    message: str
    field: str | None = None
    raw_value: Any = None

    def __post_init__(self) -> None:
        normalized_code = str(self.code).strip()
        normalized_message = str(self.message).strip()

        if not normalized_code:
            raise ValueError(
                "El código del problema de importación es obligatorio."
            )

        if not normalized_message:
            raise ValueError(
                "El mensaje del problema de importación es obligatorio."
            )

        object.__setattr__(self, "code", normalized_code)
        object.__setattr__(self, "message", normalized_message)


@dataclass(frozen=True, slots=True)
class ContractImportResult:
    """
    Resultado de procesar una fila del archivo de entrada.

    Una fila válida contiene `contract`.
    Una fila inválida contiene uno o más `issues`.
    """

    row_number: int
    contract: ContractData | None = None
    issues: tuple[ImportIssue, ...] = ()
    raw_data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.row_number < 2:
            raise ValueError(
                "El número de fila debe ser igual o superior a 2."
            )

        if self.contract is not None and self.issues:
            raise ValueError(
                "Un resultado no puede contener simultáneamente "
                "un contrato válido y problemas de importación."
            )

        if self.contract is None and not self.issues:
            raise ValueError(
                "Un resultado sin contrato debe contener al menos un problema."
            )

    @property
    def is_valid(self) -> bool:
        return self.contract is not None and not self.issues

    @property
    def is_invalid(self) -> bool:
        return not self.is_valid