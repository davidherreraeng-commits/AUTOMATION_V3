from enum import Enum


class ContractorNature(str, Enum):
    """
    Naturaleza jurídica del contratista.

    Los valores pertenecen al dominio y no a la interfaz de
    Gestión Transparente. El adaptador web será responsable de
    convertirlos a JURIDICA o NATURAL cuando interactúe con el portal.
    """

    NATURAL_PERSON = "NATURAL_PERSON"
    LEGAL_ENTITY = "LEGAL_ENTITY"