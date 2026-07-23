from __future__ import annotations

from application.dto import PortalStepVerification
from domain.enums import ContractStep
from domain.models import ContractData

from adapters.portal.gestion_transparente.components import (
    AdditionalDatesComponent,
    AvailabilityComponent,
    BudgetRegisterComponent,
    ContractHeaderComponent,
    ContractingAssistantComponent,
    GeneralDataComponent,
    PortalRecoveryComponent,
    SupervisorComponent,
)
from adapters.portal.gestion_transparente.errors import (
    PortalVerificationMismatchError,
    UnsupportedPortalStepError,
)


class GestionTransparentePortal:
    """
    Adaptador de alto nivel para Gestión Transparente.

    Traduce las etapas del dominio a operaciones semánticas de los
    componentes de interfaz.

    No contiene:

    - Selectores.
    - WebDriver.
    - WebDriverWait.
    - JavaScript.
    - Lógica de Excel.
    - Persistencia.

    Esos detalles pertenecen a los componentes concretos que serán
    inyectados posteriormente.
    """

    def __init__(
        self,
        *,
        assistant: ContractingAssistantComponent,
        header: ContractHeaderComponent,
        general_data: GeneralDataComponent,
        supervisor: SupervisorComponent,
        availability: AvailabilityComponent,
        budget_register: BudgetRegisterComponent,
        additional_dates: AdditionalDatesComponent,
        recovery: PortalRecoveryComponent,
    ) -> None:
        self._assistant = assistant
        self._header = header
        self._general_data = general_data
        self._supervisor = supervisor
        self._availability = availability
        self._budget_register = budget_register
        self._additional_dates = additional_dates
        self._recovery = recovery

    def execute_step(
        self,
        step: ContractStep,
        contract: ContractData,
    ) -> None:
        """
        Ejecuta la acción correspondiente a una etapa.

        La ejecución no confirma por sí sola el checkpoint. StepExecutor
        llamará posteriormente a verify_step().
        """

        match step:
            case ContractStep.ASSISTANT_OPENED:
                self._assistant.open(contract)

            case ContractStep.HEADER_COMPLETED:
                self._header.complete_header(contract)

            case ContractStep.HEADER_VALIDATED:
                self._header.validate_header(contract)

            case ContractStep.GENERAL_DATA_COMPLETED:
                self._general_data.complete_general_data(
                    contract
                )

            case ContractStep.CONTRACT_SAVED:
                self._general_data.save_contract(contract)

            case ContractStep.SUPERVISOR_LINKED:
                self._supervisor.link_supervisor(contract)

            case ContractStep.AVAILABILITY_LINKED:
                self._availability.link_availability(
                    contract
                )

            case ContractStep.BUDGET_REGISTER_LINKED:
                self._budget_register.link_budget_register(
                    contract
                )

            case ContractStep.ADDITIONAL_DATES_LINKED:
                self._additional_dates.link_additional_dates(
                    contract
                )

            case _:
                raise UnsupportedPortalStepError(step)

    def verify_step(
        self,
        step: ContractStep,
        contract: ContractData,
    ) -> PortalStepVerification:
        """
        Comprueba la postcondición de una etapa concreta.
        """

        match step:
            case ContractStep.ASSISTANT_OPENED:
                verification = (
                    self._assistant.verify_open(contract)
                )

            case ContractStep.HEADER_COMPLETED:
                verification = (
                    self._header.verify_header_completed(
                        contract
                    )
                )

            case ContractStep.HEADER_VALIDATED:
                verification = (
                    self._header.verify_header_validated(
                        contract
                    )
                )

            case ContractStep.GENERAL_DATA_COMPLETED:
                verification = (
                    self._general_data
                    .verify_general_data_completed(
                        contract
                    )
                )

            case ContractStep.CONTRACT_SAVED:
                verification = (
                    self._general_data
                    .verify_contract_saved(contract)
                )

            case ContractStep.SUPERVISOR_LINKED:
                verification = (
                    self._supervisor
                    .verify_supervisor_linked(contract)
                )

            case ContractStep.AVAILABILITY_LINKED:
                verification = (
                    self._availability
                    .verify_availability_linked(contract)
                )

            case ContractStep.BUDGET_REGISTER_LINKED:
                verification = (
                    self._budget_register
                    .verify_budget_register_linked(
                        contract
                    )
                )

            case ContractStep.ADDITIONAL_DATES_LINKED:
                verification = (
                    self._additional_dates
                    .verify_additional_dates_linked(
                        contract
                    )
                )

            case _:
                raise UnsupportedPortalStepError(step)

        self._validate_verification(
            requested_step=step,
            verification=verification,
        )

        return verification

    def recover(self) -> None:
        """
        Delega la recuperación general del navegador.
        """

        self._recovery.recover()

    @staticmethod
    def _validate_verification(
        *,
        requested_step: ContractStep,
        verification: PortalStepVerification,
    ) -> None:
        """
        Evita confirmar un checkpoint usando una verificación de otra
        etapa.
        """

        if verification.step != requested_step:
            raise PortalVerificationMismatchError(
                requested_step=requested_step,
                returned_step=verification.step,
            )