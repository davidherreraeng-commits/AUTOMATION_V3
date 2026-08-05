from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.input.excel.upload_validation import ExcelUploadValidator
from adapters.persistence.sqlite import SQLiteDatabaseBootstrapper
from adapters.persistence.sqlite.batch_repository import SQLiteBatchRepository
from adapters.persistence.sqlite.execution_repository import (
    SQLiteExecutionRepository,
)
from adapters.persistence.sqlite.portal_credential_repository import (
    SQLitePortalCredentialRepository,
)
from adapters.persistence.sqlite.user_repository import SQLiteUserRepository
from adapters.persistence.sqlite.real_write_authorization_repository import (
    SQLiteRealWriteAuthorizationRepository,
)
from adapters.persistence.sqlite.institutional_test_plan_repository import (
    SQLiteInstitutionalTestPlanRepository,
)
from adapters.persistence.json_execution_evidence_repository import (
    JsonExecutionEvidenceRepository,
)
from adapters.dry_run_contract_executor import DryRunContractExecutor
from application.ports.batch_execution_runner import BatchExecutionRunner
from application.ports.batch_portal_probe import BatchPortalProbe
from application.ports.contract_executor import ContractExecutor
from application.ports.contract_file_validator import ContractFileValidator
from application.ports.portal_credential_verifier import (
    PortalCredentialVerifier,
)
from application.services.batch_contract_execution_service import (
    BatchContractExecutionService,
)
from application.services.controlled_batch_contract_execution_service import (
    ControlledBatchContractExecutionService,
)
from application.services.real_write_authorization_service import (
    RealWriteAuthorizationService,
)
from application.services.institutional_test_plan_service import (
    InstitutionalTestPlanService,
)
from application.services.batch_execution_service import BatchExecutionService
from application.use_cases.execute_contract_in_session import (
    ExecuteContractInSession,
)
from application.workflow.checkpoint_service import (
    ExecutionCheckpointService,
)
from application.services.batch_portal_probe_service import (
    BatchPortalProbeService,
)
from infrastructure.config.settings import Settings
from infrastructure.security.fernet_credential_cipher import (
    FernetCredentialCipher,
)
from infrastructure.security.jwt_service import JWTService
from infrastructure.security.scrypt_password_hasher import (
    ScryptPasswordHasher,
)
from interfaces.api.routes.auth import router as auth_router
from interfaces.api.routes.batches import router as batches_router
from interfaces.api.routes.files import router as files_router
from interfaces.api.routes.portal_credentials import (
    router as portal_credentials_router,
)
from interfaces.api.routes.users import router as users_router


def create_app(
    settings: Settings | None = None,
    *,
    portal_credential_verifier: PortalCredentialVerifier | None = None,
    contract_file_validator: ContractFileValidator | None = None,
    batch_execution_runner: BatchExecutionRunner | None = None,
    batch_portal_probe: BatchPortalProbe | None = None,
    contract_executor: ContractExecutor | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_settings.ensure_runtime_directories()

        database_path = resolved_settings.resolved_database_path
        users = SQLiteUserRepository(database_path)
        portal_credentials = SQLitePortalCredentialRepository(database_path)
        batches = SQLiteBatchRepository(database_path)
        executions = SQLiteExecutionRepository(
            database_path,
            auto_initialize=False,
        )
        real_write_authorizations = (
            SQLiteRealWriteAuthorizationRepository(database_path)
        )
        institutional_test_plans = (
            SQLiteInstitutionalTestPlanRepository(database_path)
        )

        database_bootstrapper = SQLiteDatabaseBootstrapper(
            database_path,
            backup_directory=(
                resolved_settings.resolved_database_backup_directory
            ),
            backup_before_migration=(
                resolved_settings.database_backup_before_migration
            ),
        )
        database_bootstrap_report = database_bootstrapper.initialize(
            (
                users.initialize,
                portal_credentials.initialize,
                batches.initialize,
                executions.initialize,
                real_write_authorizations.initialize,
                institutional_test_plans.initialize,
            )
        )
        checkpoints = ExecutionCheckpointService(executions)

        file_validator = contract_file_validator or ExcelUploadValidator(
            upload_directory=resolved_settings.resolved_upload_directory,
            max_size_bytes=resolved_settings.upload_max_bytes,
            default_budget_year=resolved_settings.default_budget_year,
        )

        fernet_key = (
            resolved_settings.fernet_key.get_secret_value().strip()
        )
        credential_cipher = (
            FernetCredentialCipher(fernet_key)
            if fernet_key
            else None
        )

        verifier = portal_credential_verifier
        if verifier is None:
            from adapters.portal.gestion_transparente.credential_verifier import (
                SeleniumPortalCredentialVerifier,
            )

            verifier = SeleniumPortalCredentialVerifier(
                login_url=resolved_settings.portal_login_url,
                headless=(
                    resolved_settings.portal_credential_test_headless
                ),
                timeout_seconds=(
                    resolved_settings.portal_credential_test_timeout_seconds
                ),
                driver_path=resolved_settings.portal_driver_path,
                chrome_binary=resolved_settings.portal_chrome_binary,
            )

        app.state.settings = resolved_settings
        app.state.database_bootstrapper = database_bootstrapper
        app.state.database_bootstrap_report = database_bootstrap_report
        app.state.user_repository = users
        app.state.portal_credential_repository = portal_credentials
        app.state.batch_repository = batches
        app.state.execution_repository = executions
        app.state.execution_checkpoint_service = checkpoints
        app.state.contract_file_validator = file_validator
        app.state.password_hasher = ScryptPasswordHasher()
        app.state.jwt_service = JWTService(resolved_settings)
        app.state.credential_cipher = credential_cipher
        app.state.portal_credential_verifier = verifier

        resolved_contract_executor = contract_executor
        if (
            resolved_contract_executor is None
            and credential_cipher is not None
        ):
            from adapters.portal.gestion_transparente.selenium import (
                SeleniumContractPortalSessionFactory,
            )

            sessions = SeleniumContractPortalSessionFactory(
                login_url=resolved_settings.portal_login_url,
                credentials=portal_credentials,
                cipher=credential_cipher,
                headless=resolved_settings.batch_execution_headless,
                timeout_seconds=(
                    resolved_settings.batch_execution_timeout_seconds
                ),
                driver_path=resolved_settings.portal_driver_path,
                chrome_binary=resolved_settings.portal_chrome_binary,
            )
            resolved_contract_executor = ExecuteContractInSession(
                sessions=sessions,
                checkpoints=checkpoints,
            )

        real_write_enabled = (
            resolved_settings.batch_execution_enabled
            and os.getenv(
                "RPA_REAL_WRITE_AUTHORIZATION",
                "",
            ).strip().upper()
            == "INSTITUTIONALLY_AUTHORIZED"
        )

        real_contract_execution_service = (
            BatchContractExecutionService(
                batches=batches,
                credentials=portal_credentials,
                checkpoints=checkpoints,
                executor=resolved_contract_executor,
                execution_enabled=real_write_enabled,
                credential_max_age_hours=(
                    resolved_settings
                    .batch_execution_credential_max_age_hours
                ),
                reject_unit_test_values=(
                    resolved_settings
                    .batch_execution_reject_unit_test_values
                ),
            )
        )

        execution_evidence_repository = JsonExecutionEvidenceRepository(
            resolved_settings.resolved_database_path.parent
            / "execution_evidence"
        )
        execution_evidence_repository.initialize()
        app.state.execution_evidence_repository = (
            execution_evidence_repository
        )
        app.state.real_write_authorization_repository = (
            real_write_authorizations
        )
        app.state.institutional_test_plan_repository = (
            institutional_test_plans
        )
        app.state.real_write_enabled = real_write_enabled
        real_write_authorization_service = RealWriteAuthorizationService(
            repository=real_write_authorizations,
            enabled=real_write_enabled,
            ttl_seconds=(
                resolved_settings.real_write_authorization_ttl_seconds
            ),
        )
        app.state.real_write_authorization_service = (
            real_write_authorization_service
        )
        app.state.expired_real_write_authorizations = (
            real_write_authorization_service.cleanup_expired()
        )

        portal_probe = batch_portal_probe
        if portal_probe is None:
            from adapters.portal.gestion_transparente.batch_portal_probe import (
                SeleniumBatchPortalProbe,
            )

            portal_probe = SeleniumBatchPortalProbe(
                login_url=resolved_settings.portal_login_url,
                headless=resolved_settings.batch_execution_headless,
                timeout_seconds=(
                    resolved_settings.batch_execution_timeout_seconds
                ),
                driver_path=resolved_settings.portal_driver_path,
                chrome_binary=resolved_settings.portal_chrome_binary,
            )

        batch_portal_probe_service = BatchPortalProbeService(
            batches=batches,
            credentials=portal_credentials,
            cipher=credential_cipher,
            probe=portal_probe,
            credential_max_age_hours=(
                resolved_settings
                .batch_execution_credential_max_age_hours
            ),
        )
        app.state.batch_portal_probe_service = batch_portal_probe_service

        institutional_test_plan_service = InstitutionalTestPlanService(
            repository=institutional_test_plans,
            executions=real_contract_execution_service,
            portal_probe=batch_portal_probe_service,
            enabled=resolved_settings.institutional_test_plan_enabled,
            arming_enabled=(
                resolved_settings.institutional_test_plan_arming_enabled
            ),
            window_seconds=(
                resolved_settings.institutional_test_plan_window_seconds
            ),
            diagnostic_max_age_seconds=(
                resolved_settings
                .institutional_test_plan_diagnostic_max_age_seconds
            ),
        )
        app.state.institutional_test_plan_service = (
            institutional_test_plan_service
        )
        app.state.expired_institutional_test_plans = (
            institutional_test_plan_service.cleanup_expired()
        )
        app.state.batch_contract_execution_service = (
            ControlledBatchContractExecutionService(
                real_service=real_contract_execution_service,
                dry_run_executor=DryRunContractExecutor(),
                evidence=execution_evidence_repository,
                real_write_enabled=real_write_enabled,
                authorizations=real_write_authorization_service,
                institutional_plans=institutional_test_plan_service,
            )
        )

        runner = batch_execution_runner
        if runner is None:
            from adapters.execution_unavailable import (
                UnavailableBatchExecutionRunner,
            )

            runner = UnavailableBatchExecutionRunner()

        batch_execution_service = BatchExecutionService(
            batches=batches,
            credentials=portal_credentials,
            runner=runner,
            execution_enabled=(
                resolved_settings.batch_execution_enabled
            ),
            cipher_configured=credential_cipher is not None,
            credential_max_age_hours=(
                resolved_settings
                .batch_execution_credential_max_age_hours
            ),
            reject_unit_test_values=(
                resolved_settings
                .batch_execution_reject_unit_test_values
            ),
            max_workers=resolved_settings.batch_execution_workers,
        )
        app.state.batch_execution_service = batch_execution_service

        try:
            yield
        finally:
            batch_execution_service.shutdown(wait=True)

    app = FastAPI(
        title=resolved_settings.app_name,
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        auth_router,
        prefix=resolved_settings.api_prefix,
    )
    app.include_router(
        users_router,
        prefix=resolved_settings.api_prefix,
    )
    app.include_router(
        portal_credentials_router,
        prefix=resolved_settings.api_prefix,
    )
    app.include_router(
        files_router,
        prefix=resolved_settings.api_prefix,
    )
    app.include_router(
        batches_router,
        prefix=resolved_settings.api_prefix,
    )

    @app.get("/health", tags=["Sistema"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
