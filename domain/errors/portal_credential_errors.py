from __future__ import annotations


class PortalCredentialError(RuntimeError):
    """Error base de configuración de credenciales del portal."""


class PortalCredentialsNotConfiguredError(PortalCredentialError):
    """La dependencia todavía no tiene credenciales configuradas."""

    def __init__(self, dependency: str) -> None:
        super().__init__(
            "No hay credenciales de Gestión Transparente configuradas "
            f"para la dependencia '{dependency}'."
        )
        self.dependency = dependency


class PortalCredentialEncryptionError(PortalCredentialError):
    """No fue posible cifrar o descifrar la contraseña del portal."""


class PortalCredentialPermissionError(PortalCredentialError):
    """El usuario no puede administrar credenciales del portal."""

    def __init__(self) -> None:
        super().__init__(
            "Solo un superusuario puede administrar las credenciales "
            "de Gestión Transparente."
        )
