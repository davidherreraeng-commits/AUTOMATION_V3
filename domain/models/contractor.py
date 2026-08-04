from __future__ import annotations

from dataclasses import dataclass

from domain.enums import ContractorNature


@dataclass(frozen=True, slots=True)
class ContractorData:
    """
    Información normalizada del contratista.

    El documento puede conservar guion y dígito de verificación.
    La normalización específica de NIT y cédula se realizará antes
    de construir esta entidad.
    """

    document_number: str
    nature: ContractorNature

    def __post_init__(self) -> None:
        normalized_document = str(self.document_number).strip()

        if not normalized_document:
            raise ValueError(
                "El número de identificación del contratista es obligatorio."
            )

        object.__setattr__(
            self,
            "document_number",
            normalized_document,
        )