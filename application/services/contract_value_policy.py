from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from domain.models.contract import ContractData


NOMINAL_VALUE_LIMIT = Decimal("1")


def normalize_contract_number(value: object) -> str:
    """Normaliza un número contractual para comparaciones exactas."""

    return " ".join(str(value).strip().upper().split())


@dataclass(frozen=True, slots=True)
class ContractValueAssessment:
    code: str
    message: str
    blocking: bool


class ContractValuePolicy:
    """Distingue valores nominales autorizados de datos de prueba.

    Un valor igual o inferior a $1 continúa bloqueado por defecto. La única
    excepción es una coincidencia exacta del número contractual en la lista
    institucional explícita. No se admiten comodines ni coincidencias parciales.
    """

    def __init__(
        self,
        *,
        reject_nominal_values: bool = True,
        allowed_contract_numbers: Iterable[str] = (),
    ) -> None:
        self._reject_nominal_values = bool(reject_nominal_values)
        normalized = {
            normalize_contract_number(value)
            for value in allowed_contract_numbers
            if normalize_contract_number(value)
        }
        if "*" in normalized:
            raise ValueError(
                "La lista institucional de valores nominales no admite '*'."
            )
        self._allowed_contract_numbers = frozenset(normalized)

    @property
    def allowed_contract_numbers(self) -> frozenset[str]:
        return self._allowed_contract_numbers

    def assess(self, contract: ContractData) -> ContractValueAssessment | None:
        if not self._reject_nominal_values:
            return None

        nominal = (
            contract.amount <= NOMINAL_VALUE_LIMIT
            or contract.budget.gross_total <= NOMINAL_VALUE_LIMIT
        )
        if not nominal:
            return None

        contract_number = normalize_contract_number(
            contract.contract_number
        )
        if contract_number in self._allowed_contract_numbers:
            return ContractValueAssessment(
                code="NOMINAL_VALUE_INSTITUTIONALLY_ALLOWED",
                message=(
                    f"El contrato {contract.contract_number} tiene un valor "
                    "nominal institucional autorizado explícitamente. "
                    "Las demás barreras de escritura real permanecen activas."
                ),
                blocking=False,
            )

        return ContractValueAssessment(
            code="TEST_VALUES_DETECTED",
            message=(
                f"El contrato {contract.contract_number} contiene un valor "
                "igual o inferior a $1 y no tiene una autorización nominal "
                "institucional explícita. No puede enviarse al portal real."
            ),
            blocking=True,
        )
