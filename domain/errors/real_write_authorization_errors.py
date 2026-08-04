from __future__ import annotations

from uuid import UUID


class RealWriteAuthorizationError(RuntimeError):
    code = "REAL_WRITE_AUTHORIZATION_ERROR"


class RealWriteAuthorizationRepositoryError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_REPOSITORY_ERROR"


class RealWriteAuthorizationDisabledError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_DISABLED"

    def __init__(self) -> None:
        super().__init__(
            "La escritura real no está habilitada institucionalmente "
            "en el servidor."
        )


class RealWriteAuthorizationConfirmationError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_CONFIRMATION_REQUIRED"

    def __init__(self, required_confirmation: str) -> None:
        self.required_confirmation = required_confirmation
        super().__init__(
            "La confirmación para emitir la autorización temporal "
            "no coincide."
        )


class RealWriteAuthorizationRequiredError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_REQUIRED"

    def __init__(self) -> None:
        super().__init__(
            "Se requiere una autorización temporal de un solo uso "
            "para iniciar la escritura real."
        )


class RealWriteAuthorizationInvalidError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_INVALID"

    def __init__(self) -> None:
        super().__init__(
            "La autorización temporal suministrada no es válida."
        )


class RealWriteAuthorizationContextError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_CONTEXT_MISMATCH"

    def __init__(self) -> None:
        super().__init__(
            "La autorización temporal no pertenece al usuario, "
            "dependencia, lote o contrato solicitado."
        )


class RealWriteAuthorizationExpiredError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_EXPIRED"

    def __init__(self, authorization_id: UUID | None = None) -> None:
        self.authorization_id = authorization_id
        super().__init__(
            "La autorización temporal venció y debe emitirse una nueva."
        )


class RealWriteAuthorizationConsumedError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_ALREADY_CONSUMED"

    def __init__(self, authorization_id: UUID | None = None) -> None:
        self.authorization_id = authorization_id
        super().__init__(
            "La autorización temporal ya fue consumida y no puede "
            "reutilizarse."
        )


class RealWriteAuthorizationRevokedError(
    RealWriteAuthorizationError
):
    code = "REAL_WRITE_AUTHORIZATION_REVOKED"

    def __init__(self, authorization_id: UUID | None = None) -> None:
        self.authorization_id = authorization_id
        super().__init__(
            "La autorización temporal fue revocada y debe emitirse "
            "una nueva."
        )
