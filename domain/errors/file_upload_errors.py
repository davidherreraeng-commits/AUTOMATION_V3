from __future__ import annotations


class FileUploadValidationError(Exception):
    """Error base durante la recepción y validación de archivos."""


class UnsafeFileNameError(FileUploadValidationError):
    """El nombre recibido contiene rutas o caracteres no permitidos."""


class EmptyUploadedFileError(FileUploadValidationError):
    """El archivo recibido no contiene datos."""


class UnsupportedFileExtensionError(FileUploadValidationError):
    """La extensión del archivo no está autorizada."""


class FileTooLargeError(FileUploadValidationError):
    """El archivo supera el tamaño máximo configurado."""


class InvalidExcelContainerError(FileUploadValidationError):
    """El contenido no corresponde a un contenedor Excel Open XML."""


class InvalidExcelWorkbookError(FileUploadValidationError):
    """El archivo no pudo interpretarse con la estructura esperada."""
