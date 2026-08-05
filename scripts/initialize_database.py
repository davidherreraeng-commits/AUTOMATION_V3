from __future__ import annotations

import argparse
from pathlib import Path

from adapters.persistence.sqlite import (
    SQLiteBatchRepository,
    SQLiteDatabaseBootstrapper,
    SQLiteExecutionRepository,
    SQLiteInstitutionalTestPlanRepository,
    SQLitePortalCredentialRepository,
    SQLiteRealWriteAuthorizationRepository,
    SQLiteUserRepository,
)
from infrastructure.config.settings import Settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inicializa o verifica la base SQLite operativa sin eliminar "
            "datos existentes."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Ruta alternativa para la base SQLite.",
    )
    parser.add_argument(
        "--backup-directory",
        type=Path,
        default=None,
        help="Directorio alternativo para respaldos previos a migración.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="No crear respaldo antes de una migración pendiente.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    database_path = (
        args.database.expanduser().resolve()
        if args.database is not None
        else settings.resolved_database_path
    )
    backup_directory = (
        args.backup_directory.expanduser().resolve()
        if args.backup_directory is not None
        else settings.resolved_database_backup_directory
    )

    users = SQLiteUserRepository(database_path)
    credentials = SQLitePortalCredentialRepository(database_path)
    batches = SQLiteBatchRepository(database_path)
    executions = SQLiteExecutionRepository(
        database_path,
        auto_initialize=False,
    )
    authorizations = SQLiteRealWriteAuthorizationRepository(database_path)
    institutional_plans = SQLiteInstitutionalTestPlanRepository(database_path)

    report = SQLiteDatabaseBootstrapper(
        database_path,
        backup_directory=backup_directory,
        backup_before_migration=not args.no_backup,
    ).initialize(
        (
            users.initialize,
            credentials.initialize,
            batches.initialize,
            executions.initialize,
            authorizations.initialize,
            institutional_plans.initialize,
        )
    )

    print(f"Base de datos: {report.database_path}")
    print(f"Versión de esquema: {report.schema_version}")
    print(f"Base creada: {'sí' if report.created_database else 'no'}")
    print(
        "Migración aplicada: "
        + ("sí" if report.migration_applied else "no")
    )
    if report.applied_migrations:
        print("Migraciones: " + ", ".join(report.applied_migrations))
    if report.backup_path is not None:
        print(f"Respaldo previo: {report.backup_path}")
    print(f"Tablas verificadas: {len(report.tables)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
