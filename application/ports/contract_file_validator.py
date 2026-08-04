from __future__ import annotations

from typing import Protocol

from application.dto.file_validation import FileValidationOutcome


class ContractFileValidator(Protocol):
    """Puerto para validar y recuperar archivos sin exponer su ubicación."""

    def validate(
        self,
        *,
        file_name: str,
        content: bytes,
        dependency: str,
        sheet_name: str | None = None,
    ) -> FileValidationOutcome:
        ...

    def get_validation(
        self,
        *,
        validation_id: str,
        dependency: str,
    ) -> FileValidationOutcome:
        ...
