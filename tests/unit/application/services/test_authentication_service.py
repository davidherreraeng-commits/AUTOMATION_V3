from pathlib import Path

import pytest

from adapters.persistence.sqlite.user_repository import SQLiteUserRepository
from application.services.authentication_service import (
    AuthenticationService,
    InvalidCredentialsError,
)
from domain.enums.user_role import UserRole
from infrastructure.security.scrypt_password_hasher import (
    ScryptPasswordHasher,
)


def build_service(tmp_path: Path) -> tuple[
    AuthenticationService,
    SQLiteUserRepository,
    ScryptPasswordHasher,
]:
    repository = SQLiteUserRepository(tmp_path / "auth.sqlite3")
    repository.initialize()
    hasher = ScryptPasswordHasher()
    service = AuthenticationService(
        users=repository,
        password_hasher=hasher,
    )
    return service, repository, hasher


def test_should_authenticate_active_user(tmp_path: Path) -> None:
    service, repository, hasher = build_service(tmp_path)
    repository.create(
        username="carlos_herrera",
        password_hash=hasher.hash("ClaveSegura2026"),
        dependency="Adquisiciones",
        role=UserRole.OPERATOR,
    )

    user = service.authenticate(
        username="carlos_herrera",
        password="ClaveSegura2026",
    )

    assert user.username == "carlos_herrera"
    assert user.last_login_at is not None


def test_should_reject_invalid_password(tmp_path: Path) -> None:
    service, repository, hasher = build_service(tmp_path)
    repository.create(
        username="operador",
        password_hash=hasher.hash("ClaveSegura2026"),
        dependency="Proyectos",
        role=UserRole.OPERATOR,
    )

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(
            username="operador",
            password="incorrecta",
        )
