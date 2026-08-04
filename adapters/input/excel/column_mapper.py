<<<<<<< HEAD
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from adapters.input.excel.columns import (
    COLUMN_ALIASES,
    REQUIRED_CONTRACT_FIELDS,
)
from adapters.input.excel.errors import (
    DuplicateCanonicalColumnError,
    HeaderMappingError,
    MissingRequiredColumnsError,
)


def normalize_header(value: Any) -> str:
    """
    Normaliza un encabezado para poder comparar variantes:

    - Elimina tildes.
    - Convierte a minúsculas.
    - Sustituye puntuación por espacios.
    - Elimina espacios repetidos.
    """

    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = text.lower()
    text = text.replace("&", " y ")
    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    """
    Resultado de resolver los encabezados del archivo.

    `canonical_to_source` indica qué columna original alimenta cada
    campo interno.
    """

    canonical_to_source: Mapping[str, str]
    unmapped_headers: tuple[str, ...] = ()

    def canonicalize_row(
        self,
        source_row: Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Convierte una fila con encabezados originales a claves internas.
        """

        return {
            canonical_field: source_row.get(source_header)
            for canonical_field, source_header
            in self.canonical_to_source.items()
        }


class ColumnMapper:
    """
    Resuelve encabezados del Excel contra el catálogo de alias.
    """

    def __init__(
        self,
        aliases: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._aliases = aliases or COLUMN_ALIASES
        self._alias_index = self._build_alias_index()

    def _build_alias_index(self) -> dict[str, str]:
        index: dict[str, str] = {}

        for canonical_field, aliases in self._aliases.items():
            candidate_aliases = (
                canonical_field,
                *aliases,
            )

            for alias in candidate_aliases:
                normalized_alias = normalize_header(alias)

                if not normalized_alias:
                    continue

                existing_field = index.get(normalized_alias)

                if (
                    existing_field is not None
                    and existing_field != canonical_field
                ):
                    raise HeaderMappingError(
                        "El alias "
                        f"'{alias}' está asignado simultáneamente a "
                        f"'{existing_field}' y '{canonical_field}'."
                    )

                index[normalized_alias] = canonical_field

        return index

    def map_headers(
        self,
        headers: Sequence[Any],
        *,
        required_fields: Sequence[str] = REQUIRED_CONTRACT_FIELDS,
    ) -> ColumnMapping:
        canonical_to_source: dict[str, str] = {}
        unmapped_headers: list[str] = []

        for raw_header in headers:
            if raw_header is None:
                continue

            source_header = str(raw_header).strip()

            if not source_header:
                continue

            normalized_header = normalize_header(source_header)
            canonical_field = self._alias_index.get(normalized_header)

            if canonical_field is None:
                unmapped_headers.append(source_header)
                continue

            existing_header = canonical_to_source.get(canonical_field)

            if existing_header is not None:
                raise DuplicateCanonicalColumnError(
                    canonical_field=canonical_field,
                    first_header=existing_header,
                    second_header=source_header,
                )

            canonical_to_source[canonical_field] = source_header

        missing_fields = tuple(
            field
            for field in required_fields
            if field not in canonical_to_source
        )

        if missing_fields:
            raise MissingRequiredColumnsError(missing_fields)

        return ColumnMapping(
            canonical_to_source=dict(canonical_to_source),
            unmapped_headers=tuple(unmapped_headers),
=======
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from adapters.input.excel.columns import (
    COLUMN_ALIASES,
    REQUIRED_CONTRACT_FIELDS,
)
from adapters.input.excel.errors import (
    DuplicateCanonicalColumnError,
    HeaderMappingError,
    MissingRequiredColumnsError,
)


def normalize_header(value: Any) -> str:
    """
    Normaliza un encabezado para poder comparar variantes:

    - Elimina tildes.
    - Convierte a minúsculas.
    - Sustituye puntuación por espacios.
    - Elimina espacios repetidos.
    """

    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = text.lower()
    text = text.replace("&", " y ")
    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    """
    Resultado de resolver los encabezados del archivo.

    `canonical_to_source` indica qué columna original alimenta cada
    campo interno.
    """

    canonical_to_source: Mapping[str, str]
    unmapped_headers: tuple[str, ...] = ()

    def canonicalize_row(
        self,
        source_row: Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Convierte una fila con encabezados originales a claves internas.
        """

        return {
            canonical_field: source_row.get(source_header)
            for canonical_field, source_header
            in self.canonical_to_source.items()
        }


class ColumnMapper:
    """
    Resuelve encabezados del Excel contra el catálogo de alias.
    """

    def __init__(
        self,
        aliases: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._aliases = aliases or COLUMN_ALIASES
        self._alias_index = self._build_alias_index()

    def _build_alias_index(self) -> dict[str, str]:
        index: dict[str, str] = {}

        for canonical_field, aliases in self._aliases.items():
            candidate_aliases = (
                canonical_field,
                *aliases,
            )

            for alias in candidate_aliases:
                normalized_alias = normalize_header(alias)

                if not normalized_alias:
                    continue

                existing_field = index.get(normalized_alias)

                if (
                    existing_field is not None
                    and existing_field != canonical_field
                ):
                    raise HeaderMappingError(
                        "El alias "
                        f"'{alias}' está asignado simultáneamente a "
                        f"'{existing_field}' y '{canonical_field}'."
                    )

                index[normalized_alias] = canonical_field

        return index

    def map_headers(
        self,
        headers: Sequence[Any],
        *,
        required_fields: Sequence[str] = REQUIRED_CONTRACT_FIELDS,
    ) -> ColumnMapping:
        canonical_to_source: dict[str, str] = {}
        unmapped_headers: list[str] = []

        for raw_header in headers:
            if raw_header is None:
                continue

            source_header = str(raw_header).strip()

            if not source_header:
                continue

            normalized_header = normalize_header(source_header)
            canonical_field = self._alias_index.get(normalized_header)

            if canonical_field is None:
                unmapped_headers.append(source_header)
                continue

            existing_header = canonical_to_source.get(canonical_field)

            if existing_header is not None:
                raise DuplicateCanonicalColumnError(
                    canonical_field=canonical_field,
                    first_header=existing_header,
                    second_header=source_header,
                )

            canonical_to_source[canonical_field] = source_header

        missing_fields = tuple(
            field
            for field in required_fields
            if field not in canonical_to_source
        )

        if missing_fields:
            raise MissingRequiredColumnsError(missing_fields)

        return ColumnMapping(
            canonical_to_source=dict(canonical_to_source),
            unmapped_headers=tuple(unmapped_headers),
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        )