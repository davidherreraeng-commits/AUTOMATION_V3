from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from adapters.persistence.sqlite import (
    BASELINE_MIGRATION_ID,
    INSTITUTIONAL_PLAN_MIGRATION_ID,
    SQLiteBatchRepository,
    SQLiteDatabaseBootstrapper,
    SQLiteDatabaseIntegrityError,
    SQLiteExecutionRepository,
    SQLiteInstitutionalTestPlanRepository,
    SQLitePortalCredentialRepository,
    SQLiteRealWriteAuthorizationRepository,
    SQLiteUserRepository,
)
from domain.enums.user_role import UserRole


def repositories(database_path: Path):
    users = SQLiteUserRepository(database_path)
    credentials = SQLitePortalCredentialRepository(database_path)
    batches = SQLiteBatchRepository(database_path)
    executions = SQLiteExecutionRepository(
        database_path,
        auto_initialize=False,
    )
    authorizations = SQLiteRealWriteAuthorizationRepository(database_path)
    plans = SQLiteInstitutionalTestPlanRepository(database_path)
    return users, credentials, batches, executions, authorizations, plans


def initialize(database_path: Path, backup_directory: Path):
    repos = repositories(database_path)
    bootstrapper = SQLiteDatabaseBootstrapper(
        database_path,
        backup_directory=backup_directory,
    )
    report = bootstrapper.initialize(
        repository.initialize for repository in repos
    )
    return report, repos


def test_should_create_complete_database_from_empty_path(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime" / "rpa.sqlite3"
    report, _ = initialize(database_path, tmp_path / "backups")

    assert database_path.is_file()
    assert report.created_database is True
    assert report.migration_applied is True
    assert report.applied_migrations == (
        BASELINE_MIGRATION_ID,
        INSTITUTIONAL_PLAN_MIGRATION_ID,
    )
    assert report.backup_path is None
    assert "users" in report.tables
    assert "real_write_authorizations" in report.tables
    assert "rpa_schema_migrations" in report.tables


def test_should_be_idempotent_without_creating_second_backup(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "rpa.sqlite3"
    backup_directory = tmp_path / "backups"

    first, _ = initialize(database_path, backup_directory)
    second, _ = initialize(database_path, backup_directory)

    assert first.migration_applied is True
    assert second.created_database is False
    assert second.migration_applied is False
    assert second.applied_migrations == ()
    assert second.backup_path is None
    assert list(backup_directory.glob("*.sqlite3")) == []


def test_should_backup_legacy_database_and_preserve_users(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "rpa.sqlite3"
    backup_directory = tmp_path / "backups"
    users = SQLiteUserRepository(database_path)
    users.initialize()
    users.create(
        username="jefe",
        password_hash="hash-seguro",
        dependency="Adquisiciones",
        role=UserRole.SUPERUSER,
    )

    report, initialized_repositories = initialize(
        database_path,
        backup_directory,
    )
    initialized_users = initialized_repositories[0]

    assert report.created_database is False
    assert report.migration_applied is True
    assert report.backup_path is not None
    assert report.backup_path.is_file()
    assert initialized_users.find_by_username("jefe") is not None

    with sqlite3.connect(report.backup_path) as connection:
        row = connection.execute(
            "SELECT username FROM users WHERE username = 'jefe'"
        ).fetchone()
    assert row == ("jefe",)


def test_should_record_migration_once(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "rpa.sqlite3"
    initialize(database_path, tmp_path / "backups")
    initialize(database_path, tmp_path / "backups")

    with sqlite3.connect(database_path) as connection:
        baseline_count = connection.execute(
            """
            SELECT COUNT(*)
              FROM rpa_schema_migrations
             WHERE migration_id = ?
            """,
            (BASELINE_MIGRATION_ID,),
        ).fetchone()[0]
        plan_count = connection.execute(
            """
            SELECT COUNT(*)
              FROM rpa_schema_migrations
             WHERE migration_id = ?
            """,
            (INSTITUTIONAL_PLAN_MIGRATION_ID,),
        ).fetchone()[0]
        version = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

    assert baseline_count == 1
    assert plan_count == 1
    assert version == 2


def test_should_reject_corrupted_database_without_overwriting_it(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "rpa.sqlite3"
    original = b"not-a-sqlite-database"
    database_path.write_bytes(original)

    bootstrapper = SQLiteDatabaseBootstrapper(
        database_path,
        backup_directory=tmp_path / "backups",
    )

    with pytest.raises(SQLiteDatabaseIntegrityError):
        bootstrapper.initialize([])

    assert database_path.read_bytes() == original
    assert not (tmp_path / "backups").exists()
