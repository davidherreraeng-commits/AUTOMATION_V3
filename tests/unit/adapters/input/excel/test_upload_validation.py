from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from adapters.input.excel.upload_validation import ExcelUploadValidator
from domain.errors.file_upload_errors import (
    FileTooLargeError,
    InvalidExcelContainerError,
    InvalidExcelWorkbookError,
    UnsafeFileNameError,
    UnsupportedFileExtensionError,
)


VALID_HEADERS = [
    "No. de Contrato",
    "Dependencia",
    "Cédula o Nit Contratista",
    "Código del Proyecto",
    "Objeto del Contrato",
    "Fecha de Suscripción",
    "Fecha de Inicio",
    "Valor",
    "Plazo Estimado (En Dias)",
    "Modalidad o Proceso",
    "Procedimiento/Causal",
    "Tipo de Contrato",
    "Rubro Presupuestal",
    "Sub-Sector",
    "Enlace Proceso SECOP II",
    "Cédula Supervisor",
    "No. CDP",
    "No. RP",
    "Total Bruto",
]

VALID_ROW = [
    "70-2026",
    "Dependencia del archivo",
    "900469775-8",
    "I-23021-2026",
    "Servicio de software institucional.",
    "20/01/2026",
    "21/01/2026",
    "$ 1.476.190",
    180,
    "Contratación Directa",
    "Prestación de Servicios",
    "Servicios",
    "IDEA-2026 - RECURSOS CONVENIO IDEA",
    "Tecnología",
    "https://community.secop.gov.co/example",
    71693738,
    235097,
    950172,
    "$ 1.476.190",
]


def workbook_bytes(*, headers=None, rows=None) -> bytes:
    stream = BytesIO()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Contratos"
    worksheet.append(headers if headers is not None else VALID_HEADERS)
    for row in rows or []:
        worksheet.append(row)
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def build_validator(tmp_path: Path, *, max_size: int = 10_000_000):
    return ExcelUploadValidator(
        upload_directory=tmp_path / "uploads",
        max_size_bytes=max_size,
        default_budget_year=2026,
    )


def test_should_validate_and_force_authenticated_dependency(
    tmp_path: Path,
) -> None:
    outcome = build_validator(tmp_path).validate(
        file_name="contratos.xlsx",
        content=workbook_bytes(rows=[VALID_ROW]),
        dependency="Adquisiciones",
    )

    assert outcome.validation.valid_count == 1
    assert outcome.validation.invalid_count == 0
    assert outcome.can_create_batch
    assert outcome.validation.valid_contracts[0].dependency == "Adquisiciones"

    validation_directories = list((tmp_path / "uploads").rglob("validation.json"))
    assert len(validation_directories) == 1
    assert outcome.original_file_name == "contratos.xlsx"


def test_should_keep_invalid_rows_without_starting_automation(
    tmp_path: Path,
) -> None:
    invalid_row = list(VALID_ROW)
    invalid_row[0] = None

    outcome = build_validator(tmp_path).validate(
        file_name="contratos.xlsx",
        content=workbook_bytes(rows=[invalid_row]),
        dependency="Adquisiciones",
    )

    assert outcome.validation.valid_count == 0
    assert outcome.validation.invalid_count == 1
    assert not outcome.can_create_batch
    assert outcome.validation.invalid_rows[0].row_number == 2


def test_should_reject_unsafe_or_unsupported_file_names(
    tmp_path: Path,
) -> None:
    validator = build_validator(tmp_path)
    content = workbook_bytes(rows=[VALID_ROW])

    with pytest.raises(UnsafeFileNameError):
        validator.validate(
            file_name="../contratos.xlsx",
            content=content,
            dependency="Adquisiciones",
        )

    with pytest.raises(UnsupportedFileExtensionError):
        validator.validate(
            file_name="contratos.xls",
            content=content,
            dependency="Adquisiciones",
        )


def test_should_reject_fake_excel_container(tmp_path: Path) -> None:
    with pytest.raises(InvalidExcelContainerError):
        build_validator(tmp_path).validate(
            file_name="contratos.xlsx",
            content=b"not-an-excel-file",
            dependency="Adquisiciones",
        )


def test_should_reject_file_above_configured_limit(tmp_path: Path) -> None:
    content = workbook_bytes(rows=[VALID_ROW])

    with pytest.raises(FileTooLargeError):
        build_validator(tmp_path, max_size=len(content) - 1).validate(
            file_name="contratos.xlsx",
            content=content,
            dependency="Adquisiciones",
        )


def test_should_remove_storage_after_structural_excel_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(InvalidExcelWorkbookError):
        build_validator(tmp_path).validate(
            file_name="contratos.xlsx",
            content=workbook_bytes(headers=["Columna desconocida"], rows=[]),
            dependency="Adquisiciones",
        )

    upload_root = tmp_path / "uploads"
    assert not list(upload_root.rglob("contracts.xlsx"))
