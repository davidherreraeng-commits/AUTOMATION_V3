from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class PortalCredentials:
    """Credenciales cifradas de Gestión Transparente por dependencia."""

    dependency: str
    portal_username: str
    encrypted_password: str
    created_at: datetime
    updated_at: datetime
    last_tested_at: datetime | None = None
    last_test_success: bool | None = None
    last_test_code: str | None = None

    def __post_init__(self) -> None:
        dependency = str(self.dependency).strip()
        portal_username = str(self.portal_username).strip()
        encrypted_password = str(self.encrypted_password).strip()

        if not dependency:
            raise ValueError("La dependencia es obligatoria.")
        if not portal_username:
            raise ValueError("El usuario del portal es obligatorio.")
        if not encrypted_password:
            raise ValueError("La contraseña cifrada es obligatoria.")

        code = None
        if self.last_test_code is not None:
            code = str(self.last_test_code).strip() or None

        object.__setattr__(self, "dependency", dependency)
        object.__setattr__(self, "portal_username", portal_username)
        object.__setattr__(self, "encrypted_password", encrypted_password)
        object.__setattr__(
            self,
            "created_at",
            _normalize_datetime(self.created_at),
        )
        object.__setattr__(
            self,
            "updated_at",
            _normalize_datetime(self.updated_at),
        )
        object.__setattr__(
            self,
            "last_tested_at",
            _normalize_datetime(self.last_tested_at),
        )
        object.__setattr__(self, "last_test_code", code)
