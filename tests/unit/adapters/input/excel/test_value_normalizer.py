<<<<<<< HEAD
from datetime import date
from decimal import Decimal

import pytest

from adapters.input.excel import (
    ValueNormalizationError,
    ValueNormalizer,
)


def test_should_detect_missing_values() -> None:
    assert ValueNormalizer.is_missing(None)
    assert ValueNormalizer.is_missing("")
    assert ValueNormalizer.is_missing("   ")
    assert ValueNormalizer.is_missing(float("nan"))

    assert not ValueNormalizer.is_missing("0")
    assert not ValueNormalizer.is_missing(0)


def test_should_convert_integral_float_to_text_without_dot_zero() -> None:
    result = ValueNormalizer.to_text(
        1001360022.0,
        field="contractor_document",
    )

    assert result == "1001360022"


def test_should_normalize_colombian_currency() -> None:
    result = ValueNormalizer.to_decimal(
        "$ 1.476.190,50",
        field="amount",
    )

    assert result == Decimal("1476190.50")


def test_should_normalize_integer_colombian_currency() -> None:
    result = ValueNormalizer.to_decimal(
        "$ 1.476.190",
        field="amount",
    )

    assert result == Decimal("1476190")


def test_should_normalize_english_currency() -> None:
    result = ValueNormalizer.to_decimal(
        "1,476,190.50",
        field="amount",
    )

    assert result == Decimal("1476190.50")


def test_should_convert_integral_value_to_integer() -> None:
    result = ValueNormalizer.to_integer(
        "180.0",
        field="term_days",
    )

    assert result == 180


def test_should_reject_non_integral_integer() -> None:
    with pytest.raises(
        ValueNormalizationError,
        match="número entero",
    ):
        ValueNormalizer.to_integer(
            "180.5",
            field="term_days",
        )


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("20/01/2026", date(2026, 1, 20)),
        ("20-01-2026", date(2026, 1, 20)),
        ("2026-01-20", date(2026, 1, 20)),
        (date(2026, 1, 20), date(2026, 1, 20)),
    ],
)
def test_should_normalize_supported_dates(
    raw_value,
    expected,
) -> None:
    result = ValueNormalizer.to_date(
        raw_value,
        field="signing_date",
    )

    assert result == expected


def test_should_reject_missing_required_text() -> None:
    with pytest.raises(
        ValueNormalizationError,
        match="obligatorio",
    ):
        ValueNormalizer.to_text(
            " ",
            field="contract_number",
=======
from datetime import date
from decimal import Decimal

import pytest

from adapters.input.excel import (
    ValueNormalizationError,
    ValueNormalizer,
)


def test_should_detect_missing_values() -> None:
    assert ValueNormalizer.is_missing(None)
    assert ValueNormalizer.is_missing("")
    assert ValueNormalizer.is_missing("   ")
    assert ValueNormalizer.is_missing(float("nan"))

    assert not ValueNormalizer.is_missing("0")
    assert not ValueNormalizer.is_missing(0)


def test_should_convert_integral_float_to_text_without_dot_zero() -> None:
    result = ValueNormalizer.to_text(
        1001360022.0,
        field="contractor_document",
    )

    assert result == "1001360022"


def test_should_normalize_colombian_currency() -> None:
    result = ValueNormalizer.to_decimal(
        "$ 1.476.190,50",
        field="amount",
    )

    assert result == Decimal("1476190.50")


def test_should_normalize_integer_colombian_currency() -> None:
    result = ValueNormalizer.to_decimal(
        "$ 1.476.190",
        field="amount",
    )

    assert result == Decimal("1476190")


def test_should_normalize_english_currency() -> None:
    result = ValueNormalizer.to_decimal(
        "1,476,190.50",
        field="amount",
    )

    assert result == Decimal("1476190.50")


def test_should_convert_integral_value_to_integer() -> None:
    result = ValueNormalizer.to_integer(
        "180.0",
        field="term_days",
    )

    assert result == 180


def test_should_reject_non_integral_integer() -> None:
    with pytest.raises(
        ValueNormalizationError,
        match="número entero",
    ):
        ValueNormalizer.to_integer(
            "180.5",
            field="term_days",
        )


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("20/01/2026", date(2026, 1, 20)),
        ("20-01-2026", date(2026, 1, 20)),
        ("2026-01-20", date(2026, 1, 20)),
        (date(2026, 1, 20), date(2026, 1, 20)),
    ],
)
def test_should_normalize_supported_dates(
    raw_value,
    expected,
) -> None:
    result = ValueNormalizer.to_date(
        raw_value,
        field="signing_date",
    )

    assert result == expected


def test_should_reject_missing_required_text() -> None:
    with pytest.raises(
        ValueNormalizationError,
        match="obligatorio",
    ):
        ValueNormalizer.to_text(
            " ",
            field="contract_number",
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        )