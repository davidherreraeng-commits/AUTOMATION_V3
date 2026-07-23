from __future__ import annotations

from dataclasses import dataclass, field

from adapters.portal.gestion_transparente.locators.locator_registry import (
    LocatorRegistry,
)
from adapters.portal.gestion_transparente.locators.locator_spec import (
    LocatorSpec,
)


class ProfileValidationError(ValueError):
    """
    Indica que un perfil de localizadores está incompleto
    o contiene una configuración inválida.
    """


@dataclass(frozen=True, slots=True)
class PortalLocatorProfile:
    """
    Perfil versionado de localizadores del portal.

    Agrupa todos los selectores correspondientes a una estructura
    conocida de Gestión Transparente y valida que estén presentes
    las claves obligatorias.
    """

    version: str
    locators: tuple[LocatorSpec, ...]
    required_keys: frozenset[str] = field(
        default_factory=frozenset
    )

    def __post_init__(self) -> None:
        normalized_version = str(
            self.version
        ).strip()

        if not normalized_version:
            raise ProfileValidationError(
                "La versión del perfil es obligatoria."
            )

        normalized_locators = tuple(
            self.locators
        )

        if not normalized_locators:
            raise ProfileValidationError(
                "El perfil debe contener al menos un locator."
            )

        normalized_required_keys = frozenset(
            str(key).strip()
            for key in self.required_keys
            if str(key).strip()
        )

        object.__setattr__(
            self,
            "version",
            normalized_version,
        )

        object.__setattr__(
            self,
            "locators",
            normalized_locators,
        )

        object.__setattr__(
            self,
            "required_keys",
            normalized_required_keys,
        )

        # Construir el registro también valida localizadores
        # exactamente duplicados.
        registry = LocatorRegistry(
            normalized_locators
        )

        available_keys = set(
            registry.keys()
        )

        missing_keys = (
            normalized_required_keys
            - available_keys
        )

        if missing_keys:
            missing_text = ", ".join(
                sorted(missing_keys)
            )

            raise ProfileValidationError(
                "El perfil no contiene todos los localizadores "
                f"obligatorios. Faltan: {missing_text}."
            )

    @property
    def keys(self) -> frozenset[str]:
        """
        Devuelve las claves semánticas disponibles en el perfil.
        """

        return frozenset(
            locator.key
            for locator in self.locators
        )

    def build_registry(self) -> LocatorRegistry:
        """
        Construye una instancia independiente del registro.
        """

        return LocatorRegistry(
            self.locators
        )