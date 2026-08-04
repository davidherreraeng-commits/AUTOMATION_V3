from __future__ import annotations

from application.ports.password_hasher import PasswordHasher
from application.ports.user_repository import UserRepository
from domain.enums.user_role import UserRole
from domain.errors.user_errors import (
    CannotDeactivateOwnAccountError,
    CannotResetOwnPasswordError,
    UserManagementPermissionError,
    UserNotFoundError,
)
from domain.models.user_account import UserAccount


class TemporaryPasswordPolicyError(ValueError):
    """La contraseña temporal no cumple la política mínima."""


class UserManagementService:
    """Casos de uso administrativos para cuentas de la herramienta."""

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher

    def list_users(self, *, actor: UserAccount) -> list[UserAccount]:
        self._require_superuser(actor)
        return self._users.list_by_dependency(actor.dependency)

    def create_user(
        self,
        *,
        actor: UserAccount,
        username: str,
        temporary_password: str,
        role: UserRole,
    ) -> UserAccount:
        self._require_superuser(actor)
        password = self._validate_temporary_password(temporary_password)

        return self._users.create(
            username=username,
            password_hash=self._password_hasher.hash(password),
            dependency=actor.dependency,
            role=role,
            is_active=True,
            must_change_password=True,
        )

    def set_user_active(
        self,
        *,
        actor: UserAccount,
        target_user_id: int,
        is_active: bool,
    ) -> UserAccount:
        self._require_superuser(actor)
        target = self._find_accessible_user(
            actor=actor,
            target_user_id=target_user_id,
        )

        if target.user_id == actor.user_id and not is_active:
            raise CannotDeactivateOwnAccountError()

        return self._users.set_active(
            user_id=target.user_id,
            is_active=is_active,
        )

    def reset_password(
        self,
        *,
        actor: UserAccount,
        target_user_id: int,
        temporary_password: str,
    ) -> UserAccount:
        self._require_superuser(actor)
        target = self._find_accessible_user(
            actor=actor,
            target_user_id=target_user_id,
        )

        if target.user_id == actor.user_id:
            raise CannotResetOwnPasswordError()

        password = self._validate_temporary_password(temporary_password)
        return self._users.update_password(
            user_id=target.user_id,
            password_hash=self._password_hasher.hash(password),
            must_change_password=True,
        )

    def _find_accessible_user(
        self,
        *,
        actor: UserAccount,
        target_user_id: int,
    ) -> UserAccount:
        target = self._users.find_by_id(int(target_user_id))
        if target is None:
            raise UserNotFoundError(int(target_user_id))

        if target.dependency.casefold() != actor.dependency.casefold():
            # No se revela la existencia de cuentas de otra dependencia.
            raise UserNotFoundError(int(target_user_id))

        return target

    @staticmethod
    def _require_superuser(actor: UserAccount) -> None:
        if actor.role is not UserRole.SUPERUSER:
            raise UserManagementPermissionError()

    @staticmethod
    def _validate_temporary_password(value: str) -> str:
        normalized = str(value)
        if len(normalized) < 8:
            raise TemporaryPasswordPolicyError(
                "La contraseña temporal debe tener al menos 8 caracteres."
            )
        if len(normalized) > 128:
            raise TemporaryPasswordPolicyError(
                "La contraseña temporal no puede superar 128 caracteres."
            )
        return normalized
