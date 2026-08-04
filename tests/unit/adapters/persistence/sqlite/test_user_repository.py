from pathlib import Path

import pytest

from adapters.persistence.sqlite.user_repository import SQLiteUserRepository
from domain.enums.user_role import UserRole
from domain.errors.user_errors import UserAlreadyExistsError


def build_repository(tmp_path: Path) -> SQLiteUserRepository:
    repository = SQLiteUserRepository(tmp_path / "users.sqlite3")
    repository.initialize()
    return repository


def test_should_create_and_find_user_case_insensitively(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    created = repository.create(
        username="Carlos.Herrera",
        password_hash="scrypt$example",
        dependency="Adquisiciones",
        role=UserRole.SUPERUSER,
    )

    restored = repository.find_by_username("carlos.herrera")

    assert restored is not None
    assert restored.user_id == created.user_id
    assert restored.role is UserRole.SUPERUSER
    assert restored.is_superuser is True


def test_should_reject_duplicate_username(tmp_path: Path) -> None:
    repository = build_repository(tmp_path)

    repository.create(
        username="operador",
        password_hash="scrypt$one",
        dependency="Proyectos",
        role=UserRole.OPERATOR,
    )

    with pytest.raises(UserAlreadyExistsError):
        repository.create(
            username="OPERADOR",
            password_hash="scrypt$two",
            dependency="Proyectos",
            role=UserRole.OPERATOR,
        )


def test_should_list_by_dependency_and_update_active_status(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    first = repository.create(
        username="zeta",
        password_hash="scrypt$one",
        dependency="Adquisiciones",
        role=UserRole.OPERATOR,
    )
    repository.create(
        username="alfa",
        password_hash="scrypt$two",
        dependency="Adquisiciones",
        role=UserRole.SUPERUSER,
    )
    repository.create(
        username="otro",
        password_hash="scrypt$three",
        dependency="Proyectos",
        role=UserRole.OPERATOR,
    )

    users = repository.list_by_dependency("adquisiciones")
    updated = repository.set_active(
        user_id=first.user_id,
        is_active=False,
    )

    assert [user.username for user in users] == ["alfa", "zeta"]
    assert updated.is_active is False
