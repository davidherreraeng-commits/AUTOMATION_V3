from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from adapters.persistence.sqlite.user_repository import SQLiteUserRepository
from domain.enums.user_role import UserRole
from domain.errors.user_errors import UserAlreadyExistsError
from infrastructure.config.settings import Settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migra usuarios del archivo usuarios.db de la versión anterior."
        )
    )
    parser.add_argument(
        "legacy_database",
        type=Path,
        help="Ruta del usuarios.db anterior.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    legacy_path = args.legacy_database.expanduser().resolve()
    if not legacy_path.exists():
        raise SystemExit(f"No existe: {legacy_path}")

    settings = Settings()
    settings.ensure_runtime_directories()
    target = SQLiteUserRepository(settings.resolved_database_path)
    target.initialize()

    migrated = 0
    skipped = 0

    with sqlite3.connect(legacy_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT usuario, clave_hash, dependencia,
                   COALESCE(es_superusuario, 0) AS es_superusuario
              FROM usuarios
            """
        ).fetchall()

    for row in rows:
        role = (
            UserRole.SUPERUSER
            if bool(row["es_superusuario"])
            else UserRole.OPERATOR
        )
        try:
            target.create(
                username=row["usuario"],
                password_hash=row["clave_hash"],
                dependency=row["dependencia"],
                role=role,
                must_change_password=True,
            )
            migrated += 1
        except UserAlreadyExistsError:
            skipped += 1

    print(f"Migrados: {migrated}")
    print(f"Omitidos por existir: {skipped}")
    print(f"Base destino: {settings.resolved_database_path}")


if __name__ == "__main__":
    main()
