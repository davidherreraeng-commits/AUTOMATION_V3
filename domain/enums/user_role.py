from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    """Roles funcionales disponibles en la primera versión."""

    OPERATOR = "OPERATOR"
    SUPERUSER = "SUPERUSER"

    @property
    def is_superuser(self) -> bool:
        return self is UserRole.SUPERUSER
