from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from application.dto.import_result import ContractImportResult
from domain.models import ContractData


@dataclass(frozen=True, slots=True)
class BatchIssue:
    """
    Problema global detectado en el lote.

    A diferencia de ImportIssue, no necesariamente pertenece a una
    sola fila. Por ejemplo:

    - Archivo sin contratos.
    - Contratos duplicados.
    - Inconsistencia global del lote.
    """

    code: str
    message: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_code = str(self.code).strip()
        normalized_message = str(self.message).strip()

        if not normalized_code:
            raise ValueError(
                "El código del problema del lote es obligatorio."
            )

        if not normalized_message:
            raise ValueError(
                "El mensaje del problema del lote es obligatorio."
            )

        object.__setattr__(
            self,
            "code",
            normalized_code,
        )
        object.__setattr__(
            self,
            "message",
            normalized_message,
        )


@dataclass(frozen=True, slots=True)
class BatchValidationResult:
    """
    Resultado completo de validar una fuente de contratos.

    Un lote puede contener contratos válidos, pero `can_process`
    permanecerá en False si existe cualquier fila inválida o problema
    global. Esta es la política segura predeterminada.
    """

    valid_rows: tuple[ContractImportResult, ...] = ()
    invalid_rows: tuple[ContractImportResult, ...] = ()
    batch_issues: tuple[BatchIssue, ...] = ()

    def __post_init__(self) -> None:
        for result in self.valid_rows:
            if not result.is_valid:
                raise ValueError(
                    "valid_rows solamente puede contener "
                    "resultados válidos."
                )

        for result in self.invalid_rows:
            if not result.is_invalid:
                raise ValueError(
                    "invalid_rows solamente puede contener "
                    "resultados inválidos."
                )

        row_numbers = [
            result.row_number
            for result in (
                *self.valid_rows,
                *self.invalid_rows,
            )
        ]

        if len(row_numbers) != len(set(row_numbers)):
            raise ValueError(
                "Una misma fila no puede aparecer más de una vez "
                "en el resultado de validación."
            )

    @property
    def total_rows(self) -> int:
        return len(self.valid_rows) + len(self.invalid_rows)

    @property
    def valid_count(self) -> int:
        return len(self.valid_rows)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_rows)

    @property
    def valid_contracts(self) -> tuple[ContractData, ...]:
        """
        Devuelve solamente las entidades ContractData válidas.
        """

        return tuple(
            result.contract
            for result in self.valid_rows
            if result.contract is not None
        )

    @property
    def has_duplicates(self) -> bool:
        return any(
            issue.code == "DUPLICATE_CONTRACTS_IN_BATCH"
            for issue in self.batch_issues
        )

    @property
    def can_process(self) -> bool:
        """
        Política estricta:

        - Debe existir al menos un contrato válido.
        - No puede haber filas inválidas.
        - No puede haber problemas globales.

        Bajo estas condiciones puede inicializarse posteriormente
        el navegador.
        """

        return (
            bool(self.valid_rows)
            and not self.invalid_rows
            and not self.batch_issues
        )