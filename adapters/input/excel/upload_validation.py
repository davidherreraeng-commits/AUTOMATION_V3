from __future__ import annotations

import gc
import hashlib
import json
import re
import shutil
import time
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from adapters.input.excel.errors import ExcelImportError
from adapters.input.excel.excel_reader import ExcelContractSource
from adapters.input.excel.row_to_contract_mapper import ContractRowMapper
from application.dto.file_validation import FileValidationOutcome
from application.use_cases.validate_batch import ValidateBatch
from domain.errors.batch_errors import (
    StoredValidationCorruptedError,
    StoredValidationNotFoundError,
)
from domain.errors.file_upload_errors import (
    EmptyUploadedFileError,
    FileTooLargeError,
    InvalidExcelContainerError,
    InvalidExcelWorkbookError,
    UnsafeFileNameError,
    UnsupportedFileExtensionError,
)


class ExcelUploadValidator:
    """
    Almacena un Excel en un directorio aislado y ejecuta la validación.

    El adaptador nunca expone la ruta física en la respuesta. La dependencia
    se recibe desde la sesión autenticada y define el espacio de almacenamiento.
    """

    SUPPORTED_EXTENSIONS = frozenset({".xlsx", ".xlsm"})

    def __init__(
        self,
        *,
        upload_directory: str | Path,
        max_size_bytes: int,
        default_budget_year: int,
    ) -> None:
        self._upload_directory = Path(upload_directory)
        self._max_size_bytes = int(max_size_bytes)
        self._default_budget_year = int(default_budget_year)

        if self._max_size_bytes < 1:
            raise ValueError("El tamaño máximo debe ser mayor que cero.")
        if self._default_budget_year < 2000:
            raise ValueError("El año presupuestal predeterminado no es válido.")

    def validate(
        self,
        *,
        file_name: str,
        content: bytes,
        dependency: str,
        sheet_name: str | None = None,
    ) -> FileValidationOutcome:
        safe_name = self._validate_file_name(file_name)
        extension = Path(safe_name).suffix.casefold()
        self._validate_content(content=content, extension=extension)

        normalized_dependency = str(dependency).strip()
        if not normalized_dependency:
            raise ValueError("La dependencia autenticada es obligatoria.")

        normalized_sheet = str(sheet_name).strip() if sheet_name else None
        validation_id = uuid4().hex
        dependency_directory = self._dependency_directory(
            normalized_dependency
        )
        validation_directory = (
            self._upload_directory / dependency_directory / validation_id
        )
        validation_directory.mkdir(parents=True, exist_ok=False)

        stored_file_name = f"contracts{extension}"
        stored_path = validation_directory / stored_file_name

        try:
            stored_path.write_bytes(content)

            source = ExcelContractSource(
                file_path=stored_path,
                default_dependency=normalized_dependency,
                default_budget_year=self._default_budget_year,
                sheet_name=normalized_sheet,
                row_mapper=ContractRowMapper(
                    default_dependency=normalized_dependency,
                    default_budget_year=self._default_budget_year,
                    force_default_dependency=True,
                ),
            )
            result = ValidateBatch().execute(source)
            validated_at = datetime.now(UTC)

            outcome = FileValidationOutcome(
                validation_id=validation_id,
                original_file_name=safe_name,
                stored_file_name=stored_file_name,
                dependency=normalized_dependency,
                sheet_name=normalized_sheet,
                validated_at=validated_at,
                validation=result,
            )
            self._write_manifest(
                validation_directory=validation_directory,
                outcome=outcome,
            )
            return outcome
        except ExcelImportError as error:
            self._remove_validation_directory(validation_directory)
            raise InvalidExcelWorkbookError(str(error)) from error
        except Exception:
            self._remove_validation_directory(validation_directory)
            raise

    def get_validation(
        self,
        *,
        validation_id: str,
        dependency: str,
    ) -> FileValidationOutcome:
        normalized_validation_id = str(validation_id).strip().casefold()
        normalized_dependency = str(dependency).strip()

        if (
            len(normalized_validation_id) != 32
            or any(
                character not in "0123456789abcdef"
                for character in normalized_validation_id
            )
            or not normalized_dependency
        ):
            raise StoredValidationNotFoundError(normalized_validation_id)

        validation_directory = (
            self._upload_directory
            / self._dependency_directory(normalized_dependency)
            / normalized_validation_id
        )
        manifest_path = validation_directory / "validation.json"

        if not manifest_path.is_file():
            raise StoredValidationNotFoundError(normalized_validation_id)

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                str(manifest.get("validation_id", "")).casefold()
                != normalized_validation_id
                or str(manifest.get("dependency", "")).casefold()
                != normalized_dependency.casefold()
            ):
                raise StoredValidationCorruptedError(
                    "El manifiesto de validación no coincide con la sesión."
                )

            stored_file_name = str(manifest["stored_file_name"]).strip()
            if stored_file_name not in {"contracts.xlsx", "contracts.xlsm"}:
                raise StoredValidationCorruptedError(
                    "El nombre interno del archivo validado no es seguro."
                )

            stored_path = validation_directory / stored_file_name
            if not stored_path.is_file():
                raise StoredValidationCorruptedError(
                    "El archivo asociado a la validación ya no está disponible."
                )

            sheet_name = manifest.get("sheet_name")
            if sheet_name is not None:
                sheet_name = str(sheet_name).strip() or None

            source = ExcelContractSource(
                file_path=stored_path,
                default_dependency=normalized_dependency,
                default_budget_year=self._default_budget_year,
                sheet_name=sheet_name,
                row_mapper=ContractRowMapper(
                    default_dependency=normalized_dependency,
                    default_budget_year=self._default_budget_year,
                    force_default_dependency=True,
                ),
            )
            result = ValidateBatch().execute(source)
            validated_at = datetime.fromisoformat(str(manifest["validated_at"]))
            if validated_at.tzinfo is None:
                validated_at = validated_at.replace(tzinfo=UTC)
            else:
                validated_at = validated_at.astimezone(UTC)

            return FileValidationOutcome(
                validation_id=normalized_validation_id,
                original_file_name=str(manifest["original_file_name"]),
                stored_file_name=stored_file_name,
                dependency=normalized_dependency,
                sheet_name=sheet_name,
                validated_at=validated_at,
                validation=result,
            )
        except StoredValidationCorruptedError:
            raise
        except ExcelImportError as error:
            raise StoredValidationCorruptedError(
                "El archivo validado ya no puede procesarse correctamente."
            ) from error
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise StoredValidationCorruptedError(
                "El manifiesto de la validación está incompleto o dañado."
            ) from error

    @staticmethod
    def _remove_validation_directory(validation_directory: Path) -> None:
        """Elimina almacenamiento parcial, incluso ante bloqueos breves de Windows."""

        if not validation_directory.exists():
            return

        last_error: OSError | None = None

        for attempt in range(5):
            try:
                shutil.rmtree(validation_directory)
                return
            except FileNotFoundError:
                return
            except OSError as error:
                last_error = error
                gc.collect()
                time.sleep(0.05 * (attempt + 1))

        if last_error is not None:
            raise last_error

    def _validate_file_name(self, file_name: str) -> str:
        normalized = str(file_name or "").strip()
        if not normalized:
            raise UnsafeFileNameError("El nombre del archivo es obligatorio.")
        if len(normalized) > 180:
            raise UnsafeFileNameError(
                "El nombre del archivo supera los 180 caracteres."
            )
        if any(character in normalized for character in ("/", "\\", "\x00")):
            raise UnsafeFileNameError(
                "El nombre del archivo no puede contener rutas."
            )

        extension = Path(normalized).suffix.casefold()
        if extension not in self.SUPPORTED_EXTENSIONS:
            allowed = ", ".join(sorted(self.SUPPORTED_EXTENSIONS))
            raise UnsupportedFileExtensionError(
                f"Extensión no autorizada. Use uno de estos formatos: {allowed}."
            )
        return normalized

    def _validate_content(self, *, content: bytes, extension: str) -> None:
        if not content:
            raise EmptyUploadedFileError("El archivo está vacío.")
        if len(content) > self._max_size_bytes:
            max_mb = self._max_size_bytes / (1024 * 1024)
            raise FileTooLargeError(
                f"El archivo supera el límite permitido de {max_mb:g} MB."
            )
        if extension in self.SUPPORTED_EXTENSIONS and not zipfile.is_zipfile(
            BytesIO(content)
        ):
            raise InvalidExcelContainerError(
                "El contenido no corresponde a un archivo Excel válido."
            )

        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                uncompressed_size = sum(entry.file_size for entry in entries)
                if len(entries) > 10_000:
                    raise InvalidExcelContainerError(
                        "El archivo Excel contiene demasiados elementos internos."
                    )
                if uncompressed_size > self._max_size_bytes * 20:
                    raise InvalidExcelContainerError(
                        "El contenido descomprimido del Excel supera el límite seguro."
                    )
        except zipfile.BadZipFile as error:
            raise InvalidExcelContainerError(
                "El contenedor interno del Excel está dañado."
            ) from error

    @staticmethod
    def _dependency_directory(dependency: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", dependency.casefold()).strip("-")
        slug = slug[:48] or "dependency"
        digest = hashlib.sha256(dependency.casefold().encode("utf-8")).hexdigest()[:10]
        return f"{slug}-{digest}"

    @staticmethod
    def _write_manifest(
        *,
        validation_directory: Path,
        outcome: FileValidationOutcome,
    ) -> None:
        manifest = {
            "validation_id": outcome.validation_id,
            "original_file_name": outcome.original_file_name,
            "stored_file_name": outcome.stored_file_name,
            "dependency": outcome.dependency,
            "sheet_name": outcome.sheet_name,
            "validated_at": outcome.validated_at.isoformat(),
            "total_rows": outcome.validation.total_rows,
            "valid_count": outcome.validation.valid_count,
            "invalid_count": outcome.validation.invalid_count,
            "fully_valid": outcome.validation.can_process,
            "can_create_batch": outcome.can_create_batch,
        }
        (validation_directory / "validation.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
