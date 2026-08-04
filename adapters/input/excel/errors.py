<<<<<<< HEAD
from __future__ import annotations

from typing import Any


class ExcelImportError(Exception):
    """Excepción base del adaptador de entrada Excel."""


class HeaderMappingError(ExcelImportError):
    """Error relacionado con encabezados o columnas del archivo."""


class DuplicateCanonicalColumnError(HeaderMappingError):
    """
    Dos columnas del archivo representan el mismo campo interno.
    """

    def __init__(
        self,
        *,
        canonical_field: str,
        first_header: str,
        second_header: str,
    ) -> None:
        self.canonical_field = canonical_field
        self.first_header = first_header
        self.second_header = second_header

        super().__init__(
            "Se encontraron dos columnas para el mismo campo interno "
            f"'{canonical_field}': '{first_header}' y '{second_header}'."
        )


class MissingRequiredColumnsError(HeaderMappingError):
    """Faltan columnas obligatorias en el archivo."""

    def __init__(self, missing_fields: tuple[str, ...]) -> None:
        self.missing_fields = missing_fields

        super().__init__(
            "Faltan columnas obligatorias: "
            + ", ".join(missing_fields)
        )


class ValueNormalizationError(ExcelImportError):
    """
    Un valor no pudo convertirse al tipo esperado.
    """

    def __init__(
        self,
        *,
        field: str,
        raw_value: Any,
        reason: str,
    ) -> None:
        self.field = field
        self.raw_value = raw_value
        self.reason = reason

        super().__init__(
            f"No se pudo normalizar el campo '{field}'. "
            f"Valor recibido: {raw_value!r}. Motivo: {reason}"
=======
from __future__ import annotations

from typing import Any


class ExcelImportError(Exception):
    """Excepción base del adaptador de entrada Excel."""


class HeaderMappingError(ExcelImportError):
    """Error relacionado con encabezados o columnas del archivo."""


class DuplicateCanonicalColumnError(HeaderMappingError):
    """
    Dos columnas del archivo representan el mismo campo interno.
    """

    def __init__(
        self,
        *,
        canonical_field: str,
        first_header: str,
        second_header: str,
    ) -> None:
        self.canonical_field = canonical_field
        self.first_header = first_header
        self.second_header = second_header

        super().__init__(
            "Se encontraron dos columnas para el mismo campo interno "
            f"'{canonical_field}': '{first_header}' y '{second_header}'."
        )


class MissingRequiredColumnsError(HeaderMappingError):
    """Faltan columnas obligatorias en el archivo."""

    def __init__(self, missing_fields: tuple[str, ...]) -> None:
        self.missing_fields = missing_fields

        super().__init__(
            "Faltan columnas obligatorias: "
            + ", ".join(missing_fields)
        )


class ValueNormalizationError(ExcelImportError):
    """
    Un valor no pudo convertirse al tipo esperado.
    """

    def __init__(
        self,
        *,
        field: str,
        raw_value: Any,
        reason: str,
    ) -> None:
        self.field = field
        self.raw_value = raw_value
        self.reason = reason

        super().__init__(
            f"No se pudo normalizar el campo '{field}'. "
            f"Valor recibido: {raw_value!r}. Motivo: {reason}"
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        )