from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Mapping
import unicodedata


PROCESS_TYPE = "process_type"
PROCEDURE = "procedure"
CONTRACT_TYPE = "contract_type"
SUPPORTED_FIELDS = frozenset({PROCESS_TYPE, PROCEDURE, CONTRACT_TYPE})


class CatalogValueNotFoundError(ValueError):
    """Valor que no coincide con un catálogo canónico de GT."""

    def __init__(
        self,
        *,
        field: str,
        value: str,
        allowed_values: tuple[str, ...],
    ) -> None:
        self.field = field
        self.value = value
        self.allowed_values = allowed_values
        super().__init__(
            f"El valor {value!r} no existe en el catálogo {field!r}."
        )


@dataclass(frozen=True, slots=True)
class CatalogFieldDefinition:
    key: str
    label: str
    values: tuple[str, ...]
    aliases: Mapping[str, str]


class GestionTransparenteCatalog:
    """Resuelve valores de Excel hacia textos exactos del portal.

    La comparación solo normaliza mayúsculas, tildes y espacios. Las
    diferencias semánticas u ortográficas requieren un alias explícito.
    Nunca aplica similitud difusa ni elige la opción más parecida.
    """

    def __init__(
        self,
        *,
        version: str,
        fields: Mapping[str, CatalogFieldDefinition],
    ) -> None:
        self.version = str(version).strip()
        self._fields = dict(fields)
        self._indexes: dict[str, dict[str, str]] = {}

        if not self.version:
            raise ValueError("La versión del catálogo es obligatoria.")

        for field in SUPPORTED_FIELDS:
            definition = self._fields.get(field)
            if definition is None:
                raise ValueError(f"Falta el catálogo requerido: {field}.")

            index: dict[str, str] = {}
            for canonical in definition.values:
                self._register(index, canonical, canonical, field)

            for alias, canonical in definition.aliases.items():
                if canonical not in definition.values:
                    raise ValueError(
                        f"El alias {alias!r} apunta a un valor no canónico."
                    )
                self._register(index, alias, canonical, field)

            self._indexes[field] = index

    @classmethod
    def from_json(cls, path: str | Path) -> "GestionTransparenteCatalog":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        fields = {
            key: CatalogFieldDefinition(
                key=key,
                label=str(value["label"]),
                values=tuple(str(item) for item in value["values"]),
                aliases={
                    str(alias): str(canonical)
                    for alias, canonical in value.get("aliases", {}).items()
                },
            )
            for key, value in payload["fields"].items()
        }
        return cls(version=str(payload["version"]), fields=fields)

    def resolve(self, field: str, value: str) -> str:
        normalized_field = str(field).strip()
        if normalized_field not in SUPPORTED_FIELDS:
            raise ValueError(f"Catálogo no soportado: {normalized_field!r}.")

        text = str(value).strip()
        if not text:
            raise CatalogValueNotFoundError(
                field=normalized_field,
                value=text,
                allowed_values=self.values(normalized_field),
            )

        canonical = self._indexes[normalized_field].get(
            self.normalize(text)
        )
        if canonical is None:
            raise CatalogValueNotFoundError(
                field=normalized_field,
                value=text,
                allowed_values=self.values(normalized_field),
            )
        return canonical

    def try_resolve(self, field: str, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return self.resolve(field, value)
        except CatalogValueNotFoundError:
            return None

    def values(self, field: str) -> tuple[str, ...]:
        normalized_field = str(field).strip()
        definition = self._fields.get(normalized_field)
        if definition is None:
            raise ValueError(f"Catálogo no soportado: {normalized_field!r}.")
        return definition.values

    def label(self, field: str) -> str:
        normalized_field = str(field).strip()
        definition = self._fields.get(normalized_field)
        if definition is None:
            raise ValueError(f"Catálogo no soportado: {normalized_field!r}.")
        return definition.label

    @staticmethod
    def normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value))
        without_accents = "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )
        return re.sub(r"\s+", " ", without_accents).strip().casefold()

    @classmethod
    def _register(
        cls,
        index: dict[str, str],
        source: str,
        canonical: str,
        field: str,
    ) -> None:
        key = cls.normalize(source)
        existing = index.get(key)
        if existing is not None and existing != canonical:
            raise ValueError(
                f"Colisión de alias en {field}: {source!r}."
            )
        index[key] = canonical


@lru_cache(maxsize=1)
def default_gt_catalog() -> GestionTransparenteCatalog:
    path = (
        Path(__file__).resolve().parents[1]
        / "catalogs"
        / "gestion_transparente_v2026_08.json"
    )
    return GestionTransparenteCatalog.from_json(path)
