import pytest

from adapters.input.excel import (
    ColumnMapper,
    ContractField,
    DuplicateCanonicalColumnError,
    MissingRequiredColumnsError,
)


def test_should_map_known_aliases() -> None:
    mapper = ColumnMapper()

    mapping = mapper.map_headers(
        [
            "No. de Contrato",
            "Cédula o Nit Contratista",
            "Tipo Persona",
            "Código del Proyecto",
            "Columna desconocida",
        ],
        required_fields=(
            ContractField.CONTRACT_NUMBER,
            ContractField.CONTRACTOR_DOCUMENT,
            ContractField.CONTRACTOR_NATURE,
            ContractField.PROJECT_CODE,
        ),
    )

    assert mapping.canonical_to_source[
        ContractField.CONTRACT_NUMBER
    ] == "No. de Contrato"

    assert mapping.canonical_to_source[
        ContractField.CONTRACTOR_DOCUMENT
    ] == "Cédula o Nit Contratista"

    assert mapping.canonical_to_source[
        ContractField.CONTRACTOR_NATURE
    ] == "Tipo Persona"

    assert mapping.unmapped_headers == (
        "Columna desconocida",
    )


def test_should_normalize_accents_and_punctuation() -> None:
    mapper = ColumnMapper()

    mapping = mapper.map_headers(
        [
            "NUMERO DE CONTRATO",
            "CEDULA O NIT DE CONTRATISTA",
            "TIPO-DE-PERSONA",
        ],
        required_fields=(
            ContractField.CONTRACT_NUMBER,
            ContractField.CONTRACTOR_DOCUMENT,
            ContractField.CONTRACTOR_NATURE,
        ),
    )

    assert (
        ContractField.CONTRACT_NUMBER
        in mapping.canonical_to_source
    )
    assert (
        ContractField.CONTRACTOR_DOCUMENT
        in mapping.canonical_to_source
    )
    assert (
        ContractField.CONTRACTOR_NATURE
        in mapping.canonical_to_source
    )


def test_should_reject_missing_required_columns() -> None:
    mapper = ColumnMapper()

    with pytest.raises(
        MissingRequiredColumnsError,
    ) as error:
        mapper.map_headers(
            ["No. de Contrato"],
            required_fields=(
                ContractField.CONTRACT_NUMBER,
                ContractField.PROJECT_CODE,
            ),
        )

    assert error.value.missing_fields == (
        ContractField.PROJECT_CODE,
    )


def test_should_reject_duplicate_canonical_columns() -> None:
    mapper = ColumnMapper()

    with pytest.raises(
        DuplicateCanonicalColumnError,
    ):
        mapper.map_headers(
            [
                "No. CDP",
                "Código CDP",
            ],
            required_fields=(),
        )


def test_should_canonicalize_source_row() -> None:
    mapper = ColumnMapper()

    mapping = mapper.map_headers(
        [
            "No. de Contrato",
            "Código del Proyecto",
        ],
        required_fields=(
            ContractField.CONTRACT_NUMBER,
            ContractField.PROJECT_CODE,
        ),
    )

    canonical_row = mapping.canonicalize_row(
        {
            "No. de Contrato": "70-2026",
            "Código del Proyecto": "I-23021-2026",
            "Otra columna": "Ignorar",
        }
    )

    assert canonical_row == {
        ContractField.CONTRACT_NUMBER: "70-2026",
        ContractField.PROJECT_CODE: "I-23021-2026",
    }