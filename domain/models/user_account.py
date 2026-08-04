from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from domain.enums.user_role import UserRole


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class UserAccount:
    """Cuenta autenticable de un funcionario de la herramienta."""

    user_id: int
    username: str
    password_hash: str
    dependency: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    def __post_init__(self) -> None:
        username = str(self.username).strip()
        dependency = str(self.dependency).strip()
        password_hash = str(self.password_hash).strip()

        if self.user_id <= 0:
            raise ValueError("El identificador del usuario debe ser positivo.")
        if not username:
            raise ValueError("El nombre de usuario es obligatorio.")
        if not dependency:
            raise ValueError("La dependencia es obligatoria.")
        if not password_hash:
            raise ValueError("El hash de contraseña es obligatorio.")
        if not isinstance(self.role, UserRole):
            raise TypeError("El rol debe ser una instancia de UserRole.")

        object.__setattr__(self, "username", username)
        object.__setattr__(self, "dependency", dependency)
        object.__setattr__(self, "password_hash", password_hash)
        object.__setattr__(self, "is_active", bool(self.is_active))
        object.__setattr__(
            self,
            "must_change_password",
            bool(self.must_change_password),
        )
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
            "last_login_at",
            _normalize_datetime(self.last_login_at),
        )

    @property
    def is_superuser(self) -> bool:
        return self.role.is_superuser
