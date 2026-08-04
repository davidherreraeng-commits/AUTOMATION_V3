from __future__ import annotations

from datetime import datetime
from typing import Protocol

from domain.enums.user_role import UserRole
from domain.models.user_account import UserAccount


class UserRepository(Protocol):
    """Puerto de persistencia para cuentas de la herramienta."""

    def initialize(self) -> None: ...

    def find_by_id(self, user_id: int) -> UserAccount | None: ...

    def find_by_username(self, username: str) -> UserAccount | None: ...

    def list_by_dependency(self, dependency: str) -> list[UserAccount]: ...

    def create(
        self,
        *,
        username: str,
        password_hash: str,
        dependency: str,
        role: UserRole,
        is_active: bool = True,
        must_change_password: bool = False,
    ) -> UserAccount: ...

    def update_password(
        self,
        *,
        user_id: int,
        password_hash: str,
        must_change_password: bool = False,
    ) -> UserAccount: ...

    def set_active(
        self,
        *,
        user_id: int,
        is_active: bool,
    ) -> UserAccount: ...

    def record_successful_login(
        self,
        *,
        user_id: int,
        occurred_at: datetime,
    ) -> UserAccount: ...
