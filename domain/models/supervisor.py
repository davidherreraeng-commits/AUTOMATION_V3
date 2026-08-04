from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SupervisorData:
    """
    Información normalizada del interventor o supervisor.
    """

    document_number: str
    supervisor_type: str | None = None

    def __post_init__(self) -> None:
        normalized_document = str(self.document_number).strip()

        if not normalized_document:
            raise ValueError(
                "El número de identificación del supervisor es obligatorio."
            )

        object.__setattr__(
            self,
            "document_number",
            normalized_document,
        )

        if self.supervisor_type is not None:
            normalized_type = str(self.supervisor_type).strip() or None

            object.__setattr__(
                self,
                "supervisor_type",
                normalized_type,
            )