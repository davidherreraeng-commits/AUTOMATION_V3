from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from application.ports.contract_file_validator import ContractFileValidator
from domain.errors.file_upload_errors import (
    EmptyUploadedFileError,
    FileTooLargeError,
    InvalidExcelContainerError,
    InvalidExcelWorkbookError,
    UnsafeFileNameError,
    UnsupportedFileExtensionError,
)
from infrastructure.config.settings import Settings
from interfaces.api.dependencies import (
    CurrentUser,
    get_contract_file_validator,
    get_settings,
)
from interfaces.api.schemas.files import FileValidationResponse


router = APIRouter(
    prefix="/files",
    tags=["Archivos de contratos"],
)


async def _read_limited(
    upload: UploadFile,
    *,
    max_size_bytes: int,
) -> bytes:
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size_bytes:
            raise FileTooLargeError(
                "El archivo supera el tamaño máximo permitido."
            )
        chunks.append(chunk)

    return b"".join(chunks)


@router.post("/validate", response_model=FileValidationResponse)
async def validate_file(
    actor: CurrentUser,
    validator: Annotated[
        ContractFileValidator,
        Depends(get_contract_file_validator),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(...)],
    sheet_name: Annotated[str | None, Form()] = None,
) -> FileValidationResponse:
    try:
        content = await _read_limited(
            file,
            max_size_bytes=settings.upload_max_bytes,
        )
        outcome = validator.validate(
            file_name=file.filename or "",
            content=content,
            dependency=actor.dependency,
            sheet_name=sheet_name,
        )
    except FileTooLargeError as error:
        raise HTTPException(
            status_code=413,
            detail=str(error),
        ) from error
    except (
        EmptyUploadedFileError,
        InvalidExcelContainerError,
        UnsafeFileNameError,
        UnsupportedFileExtensionError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except InvalidExcelWorkbookError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    finally:
        await file.close()

    return FileValidationResponse.from_outcome(outcome)
