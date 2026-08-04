from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocatorSpec:
    """
    Candidato concreto para localizar un elemento.

    Varios LocatorSpec pueden compartir la misma key. El resolver los
    probará en orden de prioridad.
    """

    key: str
    by: str
    value: str

    priority: int = 100
    description: str | None = None

    def __post_init__(self) -> None:
        normalized_key = str(self.key).strip()
        normalized_by = str(self.by).strip()
        normalized_value = str(self.value).strip()

        if not normalized_key:
            raise ValueError(
                "La clave del locator es obligatoria."
            )

        if not normalized_by:
            raise ValueError(
                "La estrategia del locator es obligatoria."
            )

        if not normalized_value:
            raise ValueError(
                "El valor del locator es obligatorio."
            )

        if self.priority < 0:
            raise ValueError(
                "La prioridad del locator no puede ser negativa."
            )

        object.__setattr__(
            self,
            "key",
            normalized_key,
        )
        object.__setattr__(
            self,
            "by",
            normalized_by,
        )
        object.__setattr__(
            self,
            "value",
            normalized_value,
        )

        if self.description is not None:
            description = self.description.strip()

            object.__setattr__(
                self,
                "description",
                description or None,
            )

    @property
    def locator(self) -> tuple[str, str]:
        return self.by, self.value