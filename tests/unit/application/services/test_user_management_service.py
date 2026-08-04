from pathlib import Path

import pytest

from adapters.persistence.sqlite.user_repository import SQLiteUserRepository
from application.services.user_management_service import UserManagementService
from domain.enums.user_role import UserRole
from domain.errors.user_errors import (
    CannotDeactivateOwnAccountError,
    CannotResetOwnPasswordError,
    UserNotFoundError,
)
from infrastructure.security.scrypt_password_hasher import ScryptPasswordHasher


def build_service(tmp_path: Path):
    repository = SQLiteUserRepository(tmp_path / "users.sqlite3")
    repository.initialize()
    hasher = ScryptPasswordHasher()
    service = UserManagementService(
        users=repository,
        password_hasher=hasher,
    )
    actor = repository.create(
        username="jefe",
        password_hash=hasher.hash("ClaveSegura2026"),
        dependency="Adquisiciones",
        role=UserRole.SUPERUSER,
    )
    return service, repository, hasher, actor


def test_should_create_user_in_actor_dependency(tmp_path: Path) -> None:
    service, _, _, actor = build_service(tmp_path)

    created = service.create_user(
        actor=actor,
        username="operador_1",
        temporary_password="Temporal2026",
        role=UserRole.OPERATOR,
    )

    assert created.dependency == "Adquisiciones"
    assert created.role is UserRole.OPERATOR
    assert created.must_change_password is True
    assert created.is_active is True


def test_should_list_only_users_from_actor_dependency(tmp_path: Path) -> None:
    service, repository, hasher, actor = build_service(tmp_path)
    repository.create(
        username="operador_adq",
        password_hash=hasher.hash("Temporal2026"),
        dependency="Adquisiciones",
        role=UserRole.OPERATOR,
    )
    repository.create(
        username="operador_proy",
        password_hash=hasher.hash("Temporal2026"),
        dependency="Proyectos",
        role=UserRole.OPERATOR,
    )

    users = service.list_users(actor=actor)

    assert {user.username for user in users} == {"jefe", "operador_adq"}


def test_should_reject_deactivating_own_account(tmp_path: Path) -> None:
    service, _, _, actor = build_service(tmp_path)

    with pytest.raises(CannotDeactivateOwnAccountError):
        service.set_user_active(
            actor=actor,
            target_user_id=actor.user_id,
            is_active=False,
        )


def test_should_hide_user_from_another_dependency(tmp_path: Path) -> None:
    service, repository, hasher, actor = build_service(tmp_path)
    other = repository.create(
        username="otro",
        password_hash=hasher.hash("Temporal2026"),
        dependency="Proyectos",
        role=UserRole.OPERATOR,
    )

    with pytest.raises(UserNotFoundError):
        service.set_user_active(
            actor=actor,
            target_user_id=other.user_id,
            is_active=False,
        )


def test_should_reset_password_and_require_change(tmp_path: Path) -> None:
    service, repository, hasher, actor = build_service(tmp_path)
    target = repository.create(
        username="operador",
        password_hash=hasher.hash("Anterior2026"),
        dependency="Adquisiciones",
        role=UserRole.OPERATOR,
    )

    updated = service.reset_password(
        actor=actor,
        target_user_id=target.user_id,
        temporary_password="TemporalNueva2026",
    )

    assert updated.must_change_password is True
    assert hasher.verify("TemporalNueva2026", updated.password_hash) is True


def test_should_reject_resetting_own_password_from_admin_flow(
    tmp_path: Path,
) -> None:
    service, _, _, actor = build_service(tmp_path)

    with pytest.raises(CannotResetOwnPasswordError):
        service.reset_password(
            actor=actor,
            target_user_id=actor.user_id,
            temporary_password="TemporalNueva2026",
        )
