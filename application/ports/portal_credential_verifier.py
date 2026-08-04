from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PortalCredentialVerificationResult:
    """Resultado seguro de una prueba de autenticación en el portal."""

    success: bool
    code: str
    message: str

    def __post_init__(self) -> None:
        code = str(self.code).strip()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código del resultado es obligatorio.")
        if not message:
            raise ValueError("El mensaje del resultado es obligatorio.")
        object.__setattr__(self, "success", bool(self.success))
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)


class PortalCredentialVerifier(Protocol):
    """Comprueba credenciales contra Gestión Transparente."""

    def verify(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ) -> PortalCredentialVerificationResult:
        ...
