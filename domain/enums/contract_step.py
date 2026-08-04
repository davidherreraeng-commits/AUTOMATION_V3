from enum import Enum


class ContractStep(str, Enum):
    """
    Etapas persistibles del proceso de registro de un contrato.

    Cada etapa representa una postcondición comprobada, no solamente
    que se haya ejecutado un clic.
    """

    PENDING = "PENDING"
    INPUT_VALIDATED = "INPUT_VALIDATED"
    ASSISTANT_OPENED = "ASSISTANT_OPENED"

    HEADER_COMPLETED = "HEADER_COMPLETED"
    HEADER_VALIDATED = "HEADER_VALIDATED"

    GENERAL_DATA_COMPLETED = "GENERAL_DATA_COMPLETED"
    CONTRACT_SAVED = "CONTRACT_SAVED"

    SUPERVISOR_LINKED = "SUPERVISOR_LINKED"
    AVAILABILITY_LINKED = "AVAILABILITY_LINKED"
    BUDGET_REGISTER_LINKED = "BUDGET_REGISTER_LINKED"
    ADDITIONAL_DATES_LINKED = "ADDITIONAL_DATES_LINKED"
    COMPLETED = "COMPLETED"