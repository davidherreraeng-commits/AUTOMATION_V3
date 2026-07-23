from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from domain.models.budget import BudgetData
from domain.models.contractor import ContractorData
from domain.models.supervisor import SupervisorData


@dataclass(frozen=True, slots=True)
class ContractData:
    """
    Representación normalizada e inmutable de un contrato.

    Esta entidad no conoce:
    - Selenium.
    - Gestión Transparente.
    - Excel.
    - pandas.
    - FastAPI.
    - SQLite o PostgreSQL.
    """

    contract_number: str
    dependency: str

    contractor: ContractorData
    project_code: str

    object_description: str
    signing_date: date
    starting_date: date

    amount: Decimal
    term_days: int

    process_type: str
    procedure: str
    contract_type: str

    budget: BudgetData
    supervisor: SupervisorData

    secop_url: str | None = None

    guarantee_approval_date: date | None = None
    website_publication_date: date | None = None
    secop_publication_date: date | None = None

    def __post_init__(self) -> None:
        text_fields = {
            "contract_number": self.contract_number,
            "dependency": self.dependency,
            "project_code": self.project_code,
            "object_description": self.object_description,
            "process_type": self.process_type,
            "procedure": self.procedure,
            "contract_type": self.contract_type,
        }

        for field_name, field_value in text_fields.items():
            normalized_value = str(field_value).strip()

            if not normalized_value:
                raise ValueError(
                    f"El campo {field_name} es obligatorio."
                )

            object.__setattr__(
                self,
                field_name,
                normalized_value,
            )

        if self.amount <= Decimal("0"):
            raise ValueError(
                "El valor del contrato debe ser mayor que cero."
            )

        if self.term_days <= 0:
            raise ValueError(
                "El plazo estimado debe ser mayor que cero."
            )

        if self.secop_url is not None:
            normalized_url = str(self.secop_url).strip() or None

            object.__setattr__(
                self,
                "secop_url",
                normalized_url,
            )