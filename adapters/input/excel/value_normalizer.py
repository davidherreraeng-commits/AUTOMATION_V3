<<<<<<< HEAD
from __future__ import annotations

import math
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from openpyxl.utils.datetime import from_excel

from adapters.input.excel.errors import ValueNormalizationError


class ValueNormalizer:
    """
    Convierte valores provenientes de Excel a tipos consistentes.

    Controla especialmente:

    - NaN y celdas vacías.
    - Números con terminación .0.
    - Valores monetarios colombianos.
    - Fechas de Excel y fechas escritas como texto.
    """

    DATE_FORMATS: tuple[str, ...] = (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d.%m.%Y",
    )

    @staticmethod
    def is_missing(value: Any) -> bool:
        if value is None:
            return True

        if isinstance(value, str):
            normalized = value.replace("\u00a0", " ").strip()
            return normalized == ""

        if isinstance(value, float):
            return math.isnan(value)

        if isinstance(value, Decimal):
            return value.is_nan()

        # Compatibilidad sin importar pandas directamente.
        if type(value).__name__ in {
            "NAType",
            "NaTType",
        }:
            return True

        return False

    @classmethod
    def to_text(
        cls,
        value: Any,
        *,
        field: str,
        required: bool = True,
    ) -> str | None:
        if cls.is_missing(value):
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El valor es obligatorio.",
                )

            return None

        if isinstance(value, bool):
            text = "SI" if value else "NO"
        elif isinstance(value, int):
            text = str(value)
        elif isinstance(value, float):
            if value.is_integer():
                text = str(int(value))
            else:
                text = format(value, "f").rstrip("0").rstrip(".")
        elif isinstance(value, Decimal):
            if value == value.to_integral_value():
                text = str(value.to_integral_value())
            else:
                text = format(value, "f").rstrip("0").rstrip(".")
        else:
            text = str(value)

        text = text.replace("\u00a0", " ")
        text = " ".join(text.strip().split())

        if not text:
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El texto normalizado quedó vacío.",
                )

            return None

        return text

    @classmethod
    def to_integer(
        cls,
        value: Any,
        *,
        field: str,
        required: bool = True,
    ) -> int | None:
        if cls.is_missing(value):
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El valor entero es obligatorio.",
                )

            return None

        decimal_value = cls.to_decimal(
            value,
            field=field,
            required=required,
        )

        if decimal_value is None:
            return None

        if decimal_value != decimal_value.to_integral_value():
            raise ValueNormalizationError(
                field=field,
                raw_value=value,
                reason="Se esperaba un número entero.",
            )

        return int(decimal_value)

    @classmethod
    def to_decimal(
        cls,
        value: Any,
        *,
        field: str,
        required: bool = True,
    ) -> Decimal | None:
        if cls.is_missing(value):
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El valor numérico es obligatorio.",
                )

            return None

        if isinstance(value, Decimal):
            if value.is_nan():
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El valor numérico es NaN.",
                )

            return value

        if isinstance(value, bool):
            raise ValueNormalizationError(
                field=field,
                raw_value=value,
                reason="Un valor booleano no es un número válido.",
            )

        if isinstance(value, int):
            return Decimal(value)

        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El número no es finito.",
                )

            return Decimal(str(value))

        text = str(value)
        text = text.replace("\u00a0", "")
        text = text.strip()

        negative = (
            text.startswith("(")
            and text.endswith(")")
        )

        if negative:
            text = text[1:-1]

        text = re.sub(
            r"(?i)\bCOP\b",
            "",
            text,
        )
        text = text.replace("$", "")
        text = text.replace(" ", "")
        text = text.replace("'", "")

        # Conservamos únicamente caracteres numéricos relevantes.
        text = re.sub(r"[^0-9,.\-+]", "", text)

        if not text:
            raise ValueNormalizationError(
                field=field,
                raw_value=value,
                reason="No contiene caracteres numéricos.",
            )

        normalized = cls._normalize_decimal_separators(text)

        if negative and not normalized.startswith("-"):
            normalized = f"-{normalized}"

        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueNormalizationError(
                field=field,
                raw_value=value,
                reason="Formato numérico inválido.",
            ) from exc

    @staticmethod
    def _normalize_decimal_separators(text: str) -> str:
        """
        Interpreta formatos frecuentes:

        1.476.190       -> 1476190
        1.476.190,50    -> 1476190.50
        1,476,190.50    -> 1476190.50
        1476190         -> 1476190
        """

        has_dot = "." in text
        has_comma = "," in text

        if has_dot and has_comma:
            last_dot = text.rfind(".")
            last_comma = text.rfind(",")

            if last_comma > last_dot:
                # Formato colombiano/europeo:
                # puntos de miles y coma decimal.
                return (
                    text.replace(".", "")
                    .replace(",", ".")
                )

            # Formato anglosajón:
            # comas de miles y punto decimal.
            return text.replace(",", "")

        separator = None

        if has_dot:
            separator = "."
        elif has_comma:
            separator = ","

        if separator is None:
            return text

        parts = text.split(separator)

        if len(parts) > 2:
            # Si todos los bloques posteriores tienen 3 dígitos,
            # interpretamos el separador como agrupación de miles.
            if all(
                len(part) == 3
                for part in parts[1:]
            ):
                return "".join(parts)

            # El último bloque de uno o dos dígitos se interpreta
            # como parte decimal; los anteriores como miles.
            if len(parts[-1]) in {1, 2}:
                integer_part = "".join(parts[:-1])
                return f"{integer_part}.{parts[-1]}"

            return "".join(parts)

        integer_part, fractional_part = parts

        # Un único separador seguido de tres dígitos se considera
        # generalmente agrupación de miles para este dominio.
        if len(fractional_part) == 3:
            return f"{integer_part}{fractional_part}"

        if len(fractional_part) in {1, 2}:
            return f"{integer_part}.{fractional_part}"

        return f"{integer_part}{fractional_part}"

    @classmethod
    def to_date(
        cls,
        value: Any,
        *,
        field: str,
        required: bool = True,
    ) -> date | None:
        if cls.is_missing(value):
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="La fecha es obligatoria.",
                )

            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        # Compatibilidad con pandas.Timestamp sin importar pandas.
        to_pydatetime = getattr(
            value,
            "to_pydatetime",
            None,
        )

        if callable(to_pydatetime):
            converted = to_pydatetime()

            if isinstance(converted, datetime):
                return converted.date()

            if isinstance(converted, date):
                return converted

        if isinstance(value, (int, float, Decimal)):
            try:
                converted = from_excel(float(value))

                if isinstance(converted, datetime):
                    return converted.date()

                if isinstance(converted, date):
                    return converted
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="Número serial de Excel inválido.",
                ) from exc

        text = cls.to_text(
            value,
            field=field,
            required=required,
        )

        if text is None:
            return None

        # Primero intentamos formato ISO.
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass

        for date_format in cls.DATE_FORMATS:
            try:
                return datetime.strptime(
                    text,
                    date_format,
                ).date()
            except ValueError:
                continue

        raise ValueNormalizationError(
            field=field,
            raw_value=value,
            reason=(
                "Formato de fecha no reconocido. "
                "Formatos admitidos: DD/MM/AAAA, DD-MM-AAAA "
                "o AAAA-MM-DD."
            ),
=======
from __future__ import annotations

import math
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from openpyxl.utils.datetime import from_excel

from adapters.input.excel.errors import ValueNormalizationError


class ValueNormalizer:
    """
    Convierte valores provenientes de Excel a tipos consistentes.

    Controla especialmente:

    - NaN y celdas vacías.
    - Números con terminación .0.
    - Valores monetarios colombianos.
    - Fechas de Excel y fechas escritas como texto.
    """

    DATE_FORMATS: tuple[str, ...] = (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d.%m.%Y",
    )

    @staticmethod
    def is_missing(value: Any) -> bool:
        if value is None:
            return True

        if isinstance(value, str):
            normalized = value.replace("\u00a0", " ").strip()
            return normalized == ""

        if isinstance(value, float):
            return math.isnan(value)

        if isinstance(value, Decimal):
            return value.is_nan()

        # Compatibilidad sin importar pandas directamente.
        if type(value).__name__ in {
            "NAType",
            "NaTType",
        }:
            return True

        return False

    @classmethod
    def to_text(
        cls,
        value: Any,
        *,
        field: str,
        required: bool = True,
    ) -> str | None:
        if cls.is_missing(value):
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El valor es obligatorio.",
                )

            return None

        if isinstance(value, bool):
            text = "SI" if value else "NO"
        elif isinstance(value, int):
            text = str(value)
        elif isinstance(value, float):
            if value.is_integer():
                text = str(int(value))
            else:
                text = format(value, "f").rstrip("0").rstrip(".")
        elif isinstance(value, Decimal):
            if value == value.to_integral_value():
                text = str(value.to_integral_value())
            else:
                text = format(value, "f").rstrip("0").rstrip(".")
        else:
            text = str(value)

        text = text.replace("\u00a0", " ")
        text = " ".join(text.strip().split())

        if not text:
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El texto normalizado quedó vacío.",
                )

            return None

        return text

    @classmethod
    def to_integer(
        cls,
        value: Any,
        *,
        field: str,
        required: bool = True,
    ) -> int | None:
        if cls.is_missing(value):
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El valor entero es obligatorio.",
                )

            return None

        decimal_value = cls.to_decimal(
            value,
            field=field,
            required=required,
        )

        if decimal_value is None:
            return None

        if decimal_value != decimal_value.to_integral_value():
            raise ValueNormalizationError(
                field=field,
                raw_value=value,
                reason="Se esperaba un número entero.",
            )

        return int(decimal_value)

    @classmethod
    def to_decimal(
        cls,
        value: Any,
        *,
        field: str,
        required: bool = True,
    ) -> Decimal | None:
        if cls.is_missing(value):
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El valor numérico es obligatorio.",
                )

            return None

        if isinstance(value, Decimal):
            if value.is_nan():
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El valor numérico es NaN.",
                )

            return value

        if isinstance(value, bool):
            raise ValueNormalizationError(
                field=field,
                raw_value=value,
                reason="Un valor booleano no es un número válido.",
            )

        if isinstance(value, int):
            return Decimal(value)

        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="El número no es finito.",
                )

            return Decimal(str(value))

        text = str(value)
        text = text.replace("\u00a0", "")
        text = text.strip()

        negative = (
            text.startswith("(")
            and text.endswith(")")
        )

        if negative:
            text = text[1:-1]

        text = re.sub(
            r"(?i)\bCOP\b",
            "",
            text,
        )
        text = text.replace("$", "")
        text = text.replace(" ", "")
        text = text.replace("'", "")

        # Conservamos únicamente caracteres numéricos relevantes.
        text = re.sub(r"[^0-9,.\-+]", "", text)

        if not text:
            raise ValueNormalizationError(
                field=field,
                raw_value=value,
                reason="No contiene caracteres numéricos.",
            )

        normalized = cls._normalize_decimal_separators(text)

        if negative and not normalized.startswith("-"):
            normalized = f"-{normalized}"

        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueNormalizationError(
                field=field,
                raw_value=value,
                reason="Formato numérico inválido.",
            ) from exc

    @staticmethod
    def _normalize_decimal_separators(text: str) -> str:
        """
        Interpreta formatos frecuentes:

        1.476.190       -> 1476190
        1.476.190,50    -> 1476190.50
        1,476,190.50    -> 1476190.50
        1476190         -> 1476190
        """

        has_dot = "." in text
        has_comma = "," in text

        if has_dot and has_comma:
            last_dot = text.rfind(".")
            last_comma = text.rfind(",")

            if last_comma > last_dot:
                # Formato colombiano/europeo:
                # puntos de miles y coma decimal.
                return (
                    text.replace(".", "")
                    .replace(",", ".")
                )

            # Formato anglosajón:
            # comas de miles y punto decimal.
            return text.replace(",", "")

        separator = None

        if has_dot:
            separator = "."
        elif has_comma:
            separator = ","

        if separator is None:
            return text

        parts = text.split(separator)

        if len(parts) > 2:
            # Si todos los bloques posteriores tienen 3 dígitos,
            # interpretamos el separador como agrupación de miles.
            if all(
                len(part) == 3
                for part in parts[1:]
            ):
                return "".join(parts)

            # El último bloque de uno o dos dígitos se interpreta
            # como parte decimal; los anteriores como miles.
            if len(parts[-1]) in {1, 2}:
                integer_part = "".join(parts[:-1])
                return f"{integer_part}.{parts[-1]}"

            return "".join(parts)

        integer_part, fractional_part = parts

        # Un único separador seguido de tres dígitos se considera
        # generalmente agrupación de miles para este dominio.
        if len(fractional_part) == 3:
            return f"{integer_part}{fractional_part}"

        if len(fractional_part) in {1, 2}:
            return f"{integer_part}.{fractional_part}"

        return f"{integer_part}{fractional_part}"

    @classmethod
    def to_date(
        cls,
        value: Any,
        *,
        field: str,
        required: bool = True,
    ) -> date | None:
        if cls.is_missing(value):
            if required:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="La fecha es obligatoria.",
                )

            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        # Compatibilidad con pandas.Timestamp sin importar pandas.
        to_pydatetime = getattr(
            value,
            "to_pydatetime",
            None,
        )

        if callable(to_pydatetime):
            converted = to_pydatetime()

            if isinstance(converted, datetime):
                return converted.date()

            if isinstance(converted, date):
                return converted

        if isinstance(value, (int, float, Decimal)):
            try:
                converted = from_excel(float(value))

                if isinstance(converted, datetime):
                    return converted.date()

                if isinstance(converted, date):
                    return converted
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueNormalizationError(
                    field=field,
                    raw_value=value,
                    reason="Número serial de Excel inválido.",
                ) from exc

        text = cls.to_text(
            value,
            field=field,
            required=required,
        )

        if text is None:
            return None

        # Primero intentamos formato ISO.
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass

        for date_format in cls.DATE_FORMATS:
            try:
                return datetime.strptime(
                    text,
                    date_format,
                ).date()
            except ValueError:
                continue

        raise ValueNormalizationError(
            field=field,
            raw_value=value,
            reason=(
                "Formato de fecha no reconocido. "
                "Formatos admitidos: DD/MM/AAAA, DD-MM-AAAA "
                "o AAAA-MM-DD."
            ),
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        )