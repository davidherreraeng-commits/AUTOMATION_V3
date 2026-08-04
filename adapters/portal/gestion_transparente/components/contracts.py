<<<<<<< HEAD
from __future__ import annotations

from typing import Protocol

from application.dto import PortalStepVerification
from domain.models import ContractData


class ContractingAssistantComponent(Protocol):
    """Componente encargado de abrir el Asistente de Contratación."""

    def open(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_open(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class ContractHeaderComponent(Protocol):
    """
    Componente encargado de:

    - Tipo de registro.
    - Número del contrato.
    - Contratista.
    - Proyecto.
    - Validación inicial.
    """

    def complete_header(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_header_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...

    def validate_header(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_header_validated(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class GeneralDataComponent(Protocol):
    """
    Componente encargado de completar y guardar la información general.

    Más adelante podrá coordinar internamente:

    - Objeto.
    - Fechas.
    - Valor.
    - Plazo.
    - Modalidad.
    - Presupuesto.
    - SECOP.
    - Lugar de ejecución.
    """

    def complete_general_data(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_general_data_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...

    def save_contract(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_contract_saved(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class SupervisorComponent(Protocol):
    """Componente de vinculación del supervisor o interventor."""

    def link_supervisor(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_supervisor_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class AvailabilityComponent(Protocol):
    """Componente de vinculación de la disponibilidad o CDP."""

    def link_availability(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_availability_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class BudgetRegisterComponent(Protocol):
    """Componente de vinculación del registro presupuestal."""

    def link_budget_register(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_budget_register_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class AdditionalDatesComponent(Protocol):
    """Componente de vinculación de fechas adicionales."""

    def link_additional_dates(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_additional_dates_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class PortalRecoveryComponent(Protocol):
    """
    Estrategia general de recuperación del navegador.

    Posteriormente podrá:

    - Cerrar diálogos abiertos.
    - Recargar la página.
    - Volver al asistente.
    - Comprobar la sesión.
    """

    def recover(self) -> None:
=======
from __future__ import annotations

from typing import Protocol

from application.dto import PortalStepVerification
from domain.models import ContractData


class ContractingAssistantComponent(Protocol):
    """Componente encargado de abrir el Asistente de Contratación."""

    def open(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_open(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class ContractHeaderComponent(Protocol):
    """
    Componente encargado de:

    - Tipo de registro.
    - Número del contrato.
    - Contratista.
    - Proyecto.
    - Validación inicial.
    """

    def complete_header(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_header_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...

    def validate_header(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_header_validated(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class GeneralDataComponent(Protocol):
    """
    Componente encargado de completar y guardar la información general.

    Más adelante podrá coordinar internamente:

    - Objeto.
    - Fechas.
    - Valor.
    - Plazo.
    - Modalidad.
    - Presupuesto.
    - SECOP.
    - Lugar de ejecución.
    """

    def complete_general_data(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_general_data_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...

    def save_contract(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_contract_saved(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class SupervisorComponent(Protocol):
    """Componente de vinculación del supervisor o interventor."""

    def link_supervisor(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_supervisor_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class AvailabilityComponent(Protocol):
    """Componente de vinculación de la disponibilidad o CDP."""

    def link_availability(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_availability_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class BudgetRegisterComponent(Protocol):
    """Componente de vinculación del registro presupuestal."""

    def link_budget_register(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_budget_register_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class AdditionalDatesComponent(Protocol):
    """Componente de vinculación de fechas adicionales."""

    def link_additional_dates(
        self,
        contract: ContractData,
    ) -> None:
        ...

    def verify_additional_dates_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        ...


class PortalRecoveryComponent(Protocol):
    """
    Estrategia general de recuperación del navegador.

    Posteriormente podrá:

    - Cerrar diálogos abiertos.
    - Recargar la página.
    - Volver al asistente.
    - Comprobar la sesión.
    """

    def recover(self) -> None:
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        ...