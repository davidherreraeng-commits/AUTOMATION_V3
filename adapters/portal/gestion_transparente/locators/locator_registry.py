<<<<<<< HEAD
from __future__ import annotations

from collections.abc import Iterable

from adapters.portal.gestion_transparente.locators.locator_spec import (
    LocatorSpec,
)


class LocatorRegistryError(RuntimeError):
    """Error base del registro de localizadores."""


class LocatorNotRegisteredError(
    LocatorRegistryError,
    KeyError,
):
    """No existe ningún localizador para la clave indicada."""

    def __init__(self, key: str) -> None:
        self.key = key

        super().__init__(
            f"No existen localizadores registrados para '{key}'."
        )


class DuplicateLocatorError(
    LocatorRegistryError
):
    """Se intentó registrar exactamente el mismo locator dos veces."""


class LocatorRegistry:
    """
    Registro de localizadores semánticos.

    Una clave puede tener varios candidatos para soportar:

    - Variaciones del portal.
    - Selectores alternativos.
    - Migraciones graduales de perfil.
    """

    def __init__(
        self,
        locators: Iterable[LocatorSpec] = (),
    ) -> None:
        self._locators: dict[
            str,
            list[LocatorSpec],
        ] = {}

        self.extend(locators)

    def register(
        self,
        locator: LocatorSpec,
    ) -> None:
        candidates = self._locators.setdefault(
            locator.key,
            [],
        )

        duplicate = any(
            candidate.by == locator.by
            and candidate.value == locator.value
            for candidate in candidates
        )

        if duplicate:
            raise DuplicateLocatorError(
                "El locator ya se encuentra registrado: "
                f"{locator.key} -> "
                f"({locator.by}, {locator.value})."
            )

        candidates.append(locator)

        candidates.sort(
            key=lambda candidate: candidate.priority
        )

    def extend(
        self,
        locators: Iterable[LocatorSpec],
    ) -> None:
        for locator in locators:
            self.register(locator)

    def candidates(
        self,
        key: str,
    ) -> tuple[LocatorSpec, ...]:
        normalized_key = str(key).strip()

        if (
            not normalized_key
            or normalized_key not in self._locators
        ):
            raise LocatorNotRegisteredError(
                normalized_key
            )

        return tuple(
            self._locators[normalized_key]
        )

    def keys(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._locators)
        )

    def __contains__(self, key: object) -> bool:
        return (
            isinstance(key, str)
            and key.strip() in self._locators
        )

    def __len__(self) -> int:
=======
from __future__ import annotations

from collections.abc import Iterable

from adapters.portal.gestion_transparente.locators.locator_spec import (
    LocatorSpec,
)


class LocatorRegistryError(RuntimeError):
    """Error base del registro de localizadores."""


class LocatorNotRegisteredError(
    LocatorRegistryError,
    KeyError,
):
    """No existe ningún localizador para la clave indicada."""

    def __init__(self, key: str) -> None:
        self.key = key

        super().__init__(
            f"No existen localizadores registrados para '{key}'."
        )


class DuplicateLocatorError(
    LocatorRegistryError
):
    """Se intentó registrar exactamente el mismo locator dos veces."""


class LocatorRegistry:
    """
    Registro de localizadores semánticos.

    Una clave puede tener varios candidatos para soportar:

    - Variaciones del portal.
    - Selectores alternativos.
    - Migraciones graduales de perfil.
    """

    def __init__(
        self,
        locators: Iterable[LocatorSpec] = (),
    ) -> None:
        self._locators: dict[
            str,
            list[LocatorSpec],
        ] = {}

        self.extend(locators)

    def register(
        self,
        locator: LocatorSpec,
    ) -> None:
        candidates = self._locators.setdefault(
            locator.key,
            [],
        )

        duplicate = any(
            candidate.by == locator.by
            and candidate.value == locator.value
            for candidate in candidates
        )

        if duplicate:
            raise DuplicateLocatorError(
                "El locator ya se encuentra registrado: "
                f"{locator.key} -> "
                f"({locator.by}, {locator.value})."
            )

        candidates.append(locator)

        candidates.sort(
            key=lambda candidate: candidate.priority
        )

    def extend(
        self,
        locators: Iterable[LocatorSpec],
    ) -> None:
        for locator in locators:
            self.register(locator)

    def candidates(
        self,
        key: str,
    ) -> tuple[LocatorSpec, ...]:
        normalized_key = str(key).strip()

        if (
            not normalized_key
            or normalized_key not in self._locators
        ):
            raise LocatorNotRegisteredError(
                normalized_key
            )

        return tuple(
            self._locators[normalized_key]
        )

    def keys(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._locators)
        )

    def __contains__(self, key: object) -> bool:
        return (
            isinstance(key, str)
            and key.strip() in self._locators
        )

    def __len__(self) -> int:
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        return len(self._locators)