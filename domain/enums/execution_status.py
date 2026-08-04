<<<<<<< HEAD
from enum import Enum


class ExecutionStatus(str, Enum):
    """
    Estado operacional de una ejecución.

    El estado indica qué está ocurriendo con el procesamiento,
    mientras ContractStep indica hasta dónde llegó el contrato.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"

    RETRY_PENDING = "RETRY_PENDING"
    MANUAL_REVIEW = "MANUAL_REVIEW"

    ALREADY_EXISTS = "ALREADY_EXISTS"
    COMPLETED = "COMPLETED"
=======
from enum import Enum


class ExecutionStatus(str, Enum):
    """
    Estado operacional de una ejecución.

    El estado indica qué está ocurriendo con el procesamiento,
    mientras ContractStep indica hasta dónde llegó el contrato.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"

    RETRY_PENDING = "RETRY_PENDING"
    MANUAL_REVIEW = "MANUAL_REVIEW"

    ALREADY_EXISTS = "ALREADY_EXISTS"
    COMPLETED = "COMPLETED"
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
    FAILED = "FAILED"