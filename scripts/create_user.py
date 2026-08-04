from __future__ import annotations

import argparse
import getpass

from adapters.persistence.sqlite.user_repository import SQLiteUserRepository
from domain.enums.user_role import UserRole
from infrastructure.config.settings import Settings
from infrastructure.security.scrypt_password_hasher import (
    ScryptPasswordHasher,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea un usuario inicial de la herramienta RPA."
    )
    parser.add_argument("--username", required=True)
    parser.add_argument("--dependency", required=True)
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.SUPERUSER.value,
    )
    parser.add_argument(
        "--must-change-password",
        action="store_true",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    password = getpass.getpass("Contraseña: ")
    confirmation = getpass.getpass("Confirmar contraseña: ")

    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden.")
    if len(password) < 8:
        raise SystemExit("La contraseña debe tener al menos 8 caracteres.")

    settings = Settings()
    settings.ensure_runtime_directories()

    repository = SQLiteUserRepository(
        settings.resolved_database_path
    )
    repository.initialize()

    user = repository.create(
        username=args.username,
        password_hash=ScryptPasswordHasher().hash(password),
        dependency=args.dependency,
        role=UserRole(args.role),
        must_change_password=args.must_change_password,
    )

    print(
        "Usuario creado:",
        user.username,
        "| dependencia:",
        user.dependency,
        "| rol:",
        user.role.value,
    )


if __name__ == "__main__":
    main()
