from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BudgetData:
    """
    Información presupuestal necesaria para vincular:

    - Rubro.
    - CDP.
    - Registro presupuestal.
    """

    year: int
    item: str
    subsector: str
    cdp_code: str
    gross_total: Decimal

    budget_register_number: str | None = None
    budget_register_date: date | None = None

    def __post_init__(self) -> None:
        if self.year < 2000:
            raise ValueError(
                f"El año presupuestal no es válido: {self.year}"
            )

        normalized_item = str(self.item).strip()
        normalized_subsector = str(self.subsector).strip()
        normalized_cdp = str(self.cdp_code).strip()

        if not normalized_item:
            raise ValueError("El rubro presupuestal es obligatorio.")

        if not normalized_subsector:
            raise ValueError("El sub-sector es obligatorio.")

        if not normalized_cdp:
            raise ValueError("El código CDP es obligatorio.")

        if self.gross_total < Decimal("0"):
            raise ValueError(
                "El total bruto no puede ser negativo."
            )

        object.__setattr__(self, "item", normalized_item)
        object.__setattr__(self, "subsector", normalized_subsector)
        object.__setattr__(self, "cdp_code", normalized_cdp)

        if self.budget_register_number is not None:
            normalized_register = (
                str(self.budget_register_number).strip() or None
            )

            object.__setattr__(
                self,
                "budget_register_number",
                normalized_register,
            )