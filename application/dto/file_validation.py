from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.dto.batch_validation import BatchValidationResult


@dataclass(frozen=True, slots=True)
class FileValidationOutcome:
    """Resultado de almacenar y validar un archivo de contratos."""

    validation_id: str
    original_file_name: str
    stored_file_name: str
    dependency: str
    sheet_name: str | None
    validated_at: datetime
    validation: BatchValidationResult

    @property
    def can_create_batch(self) -> bool:
        """Permite preparar un lote cuando existe al menos una fila válida."""

        return self.validation.valid_count > 0
