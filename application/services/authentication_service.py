from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from application.ports.password_hasher import PasswordHasher
from application.ports.user_repository import UserRepository
from domain.models.user_account import UserAccount


class AuthenticationError(Exception):
    """Error base del proceso de autenticación."""


class InvalidCredentialsError(AuthenticationError):
    pass


class InactiveUserError(AuthenticationError):
    pass


class PasswordPolicyError(AuthenticationError):
    pass


class AuthenticationService:
    """Casos de uso de autenticación independientes de FastAPI."""

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._dummy_hash = password_hasher.hash(
            "dummy-password-not-used"
        )

    def authenticate(
        self,
        *,
        username: str,
        password: str,
    ) -> UserAccount:
        normalized_username = str(username).strip()

        if not normalized_username or not password:
            raise InvalidCredentialsError()

        user = self._users.find_by_username(normalized_username)

        if user is None:
            self._password_hasher.verify(password, self._dummy_hash)
            raise InvalidCredentialsError()

        if not self._password_hasher.verify(
            password,
            user.password_hash,
        ):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InactiveUserError()

        if self._password_hasher.needs_rehash(user.password_hash):
            upgraded_hash = self._password_hasher.hash(password)
            user = self._users.update_password(
                user_id=user.user_id,
                password_hash=upgraded_hash,
                must_change_password=user.must_change_password,
            )

        return self._users.record_successful_login(
            user_id=user.user_id,
            occurred_at=datetime.now(timezone.utc),
        )

    def change_password(
        self,
        *,
        user: UserAccount,
        current_password: str,
        new_password: str,
    ) -> UserAccount:
        if not self._password_hasher.verify(
            current_password,
            user.password_hash,
        ):
            raise InvalidCredentialsError()

        normalized = str(new_password)
        if len(normalized) < 8:
            raise PasswordPolicyError(
                "La nueva contraseña debe tener al menos 8 caracteres."
            )
        if len(normalized) > 128:
            raise PasswordPolicyError(
                "La nueva contraseña no puede superar 128 caracteres."
            )
        if normalized == current_password:
            raise PasswordPolicyError(
                "La nueva contraseña debe ser diferente a la actual."
            )

        return self._users.update_password(
            user_id=user.user_id,
            password_hash=self._password_hasher.hash(normalized),
            must_change_password=False,
        )
