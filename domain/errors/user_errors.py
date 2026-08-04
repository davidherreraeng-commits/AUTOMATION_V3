from __future__ import annotations


class UserAccountError(Exception):
    """Error base relacionado con cuentas de usuario."""


class UserAlreadyExistsError(UserAccountError):
    def __init__(self, username: str) -> None:
        super().__init__(f"Ya existe el usuario '{username}'.")
        self.username = username


class UserNotFoundError(UserAccountError):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"No existe el usuario con id {user_id}.")
        self.user_id = user_id


class UserManagementPermissionError(UserAccountError):
    def __init__(self) -> None:
        super().__init__(
            "No tiene permisos para administrar cuentas de usuario."
        )


class CannotDeactivateOwnAccountError(UserAccountError):
    def __init__(self) -> None:
        super().__init__(
            "No puede desactivar la cuenta con la que inició sesión."
        )


class CannotResetOwnPasswordError(UserAccountError):
    def __init__(self) -> None:
        super().__init__(
            "Use la opción Cambiar contraseña para actualizar su propia cuenta."
        )
