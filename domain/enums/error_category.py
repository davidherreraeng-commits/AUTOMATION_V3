<<<<<<< HEAD
from enum import Enum


class ErrorCategory(str, Enum):
    """
    Clasificación general de errores del módulo de automatización.
    """

    INPUT_VALIDATION = "INPUT_VALIDATION"
    BUSINESS_RULE = "BUSINESS_RULE"

    PORTAL_VALIDATION = "PORTAL_VALIDATION"
    PORTAL_STRUCTURE = "PORTAL_STRUCTURE"

    LOCATOR = "LOCATOR"
    TIMEOUT = "TIMEOUT"
    SESSION = "SESSION"

    INFRASTRUCTURE = "INFRASTRUCTURE"
=======
from enum import Enum


class ErrorCategory(str, Enum):
    """
    Clasificación general de errores del módulo de automatización.
    """

    INPUT_VALIDATION = "INPUT_VALIDATION"
    BUSINESS_RULE = "BUSINESS_RULE"

    PORTAL_VALIDATION = "PORTAL_VALIDATION"
    PORTAL_STRUCTURE = "PORTAL_STRUCTURE"

    LOCATOR = "LOCATOR"
    TIMEOUT = "TIMEOUT"
    SESSION = "SESSION"

    INFRASTRUCTURE = "INFRASTRUCTURE"
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
    UNKNOWN = "UNKNOWN"