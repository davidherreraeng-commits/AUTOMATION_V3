from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.batch_repository import SQLiteBatchRepository
from adapters.persistence.sqlite.portal_credential_repository import (
    SQLitePortalCredentialRepository,
)
from application.ports.batch_portal_probe import (
    BatchGeneralDataDraftProbeResult,
    BatchPortalProbeResult,
)
from application.services.batch_portal_probe_service import (
    BatchPortalProbeService,
)
from domain.enums.batch_status import BatchStatus
from domain.errors.batch_portal_probe_errors import (
    BatchPortalProbeBlockedError,
    BatchPortalProbeConfigurationError,
)
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData
from domain.models.contract_batch import BatchContract, ContractBatch
from domain.enums.contractor_nature import ContractorNature


class FakeCipher:
    def __init__(self) -> None:
        self.last_ciphertext: str | None = None

    def encrypt(self, plaintext: str) -> str:
        return f"encrypted::{plaintext}"

    def decrypt(self, ciphertext: str) -> str:
        self.last_ciphertext = ciphertext
        return "ClavePortal2026"


class FakeProbe:
    name = "fake-navigation-probe"

    def __init__(self) -> None:
        self.username: str | None = None
        self.password: str | None = None

    def probe(self, *, portal_username: str, portal_password: str):
        self.username = portal_username
        self.password = portal_password
        return BatchPortalProbeResult(
            success=True,
            code="NAVIGATION_READY",
            message="Navegación disponible.",
            authenticated=True,
            contracting_menu_found=True,
            enter_contract_found=True,
            assistant_access_found=True,
            duration_ms=1250,
        )

    def probe_general_data_draft(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchGeneralDataDraftProbeResult:
        self.username = portal_username
        self.password = portal_password
        return BatchGeneralDataDraftProbeResult(
            success=True,
            code="GENERAL_DATA_DRAFT_READY",
            message="C5 confirmado sin validar ni guardar.",
            authenticated=True,
            assistant_opened=True,
            header_validation_confirmed=True,
            object_written=True,
            signing_date_written=True,
            starting_date_written=True,
            amount_written=True,
            amount_in_words_generated=True,
            contract_term_written=True,
            term_unit_days_selected=True,
            process_type_selected=True,
            procedure_selected=True,
            contract_type_selected=True,
            other_currency_no_selected=True,
            general_data_completed=True,
            general_validate_clicked=False,
            save_clicked=False,
            duration_ms=900,
        )


def contract() -> ContractData:
    return ContractData(
        contract_number="70-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.LEGAL_ENTITY,
            document_number="900469775-8",
        ),
        project_code="I-23021-2026",
        object_description="Servicio institucional.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1476190"),
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="IDEA-2026",
            subsector="Tecnología",
            cdp_code="235097",
            budget_register_number="950172",
            gross_total=Decimal("1476190"),
        ),
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Interno",
        ),
        secop_url="https://community.secop.gov.co/example",
    )


def repositories(tmp_path: Path):
    batches = SQLiteBatchRepository(tmp_path / "db.sqlite3")
    batches.initialize()
    credentials = SQLitePortalCredentialRepository(tmp_path / "db.sqlite3")
    credentials.initialize()
    return batches, credentials


def create_batch(
    batches: SQLiteBatchRepository,
    *,
    status: BatchStatus = BatchStatus.READY,
) -> ContractBatch:
    now = datetime.now(UTC)
    batch = ContractBatch(
        batch_id=uuid4(),
        validation_id="a" * 32,
        source_file_name="contratos.xlsx",
        dependency="Adquisiciones",
        created_by_user_id=1,
        created_by_username="jefe",
        status=BatchStatus.READY,
        contracts=(
            BatchContract(
                item_id=uuid4(),
                source_row_number=2,
                contract=contract(),
            ),
        ),
        created_at=now,
        updated_at=now,
    )
    stored = batches.create(batch)
    if status is BatchStatus.PROCESSING:
        return batches.claim_for_processing(
            stored.batch_id,
            dependency="Adquisiciones",
        )
    if status is BatchStatus.CANCELLED:
        return batches.cancel_ready(
            stored.batch_id,
            dependency="Adquisiciones",
        )
    return stored


def configure_credentials(
    credentials: SQLitePortalCredentialRepository,
    *,
    tested_at: datetime | None = None,
    success: bool = True,
) -> None:
    credentials.upsert(
        dependency="Adquisiciones",
        portal_username="usuario.gt",
        encrypted_password="encrypted-value",
    )
    credentials.record_test_result(
        dependency="Adquisiciones",
        tested_at=tested_at or datetime.now(UTC),
        success=success,
        code="AUTHENTICATED" if success else "INVALID_CREDENTIALS",
    )


def test_should_decrypt_credentials_and_return_safe_probe_outcome(
    tmp_path: Path,
) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches)
    configure_credentials(credentials)
    cipher = FakeCipher()
    probe = FakeProbe()
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=cipher,
        probe=probe,
    )

    outcome = service.run(
        batch_id=batch.batch_id,
        dependency="Adquisiciones",
    )

    assert outcome.success is True
    assert outcome.code == "NAVIGATION_READY"
    assert outcome.assistant_access_found is True
    assert outcome.duration_ms == 1250
    assert cipher.last_ciphertext == "encrypted-value"
    assert probe.username == "usuario.gt"
    assert probe.password == "ClavePortal2026"
    assert "ClavePortal2026" not in outcome.message



def test_should_allow_processing_batch_for_supervised_diagnostic(
    tmp_path: Path,
) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches, status=BatchStatus.PROCESSING)
    configure_credentials(credentials)
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=FakeProbe(),
    )

    outcome = service.run(
        batch_id=batch.batch_id,
        dependency="Adquisiciones",
        allow_processing=True,
    )

    assert outcome.success is True
    assert outcome.batch_id == batch.batch_id


def test_general_data_draft_should_allow_processing_batch_without_writes(
    tmp_path: Path,
) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches, status=BatchStatus.PROCESSING)
    configure_credentials(credentials)
    probe = FakeProbe()
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=probe,
    )

    outcome = service.run_general_data_draft(
        batch_id=batch.batch_id,
        item_id=batch.contracts[0].item_id,
        dependency="Adquisiciones",
    )

    assert outcome.success is True
    assert outcome.code == "GENERAL_DATA_DRAFT_READY"
    assert outcome.procedure_selected is True
    assert outcome.general_validate_clicked is False
    assert outcome.save_clicked is False


def test_should_reject_processing_batch_without_explicit_permission(
    tmp_path: Path,
) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches, status=BatchStatus.PROCESSING)
    configure_credentials(credentials)
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=FakeProbe(),
    )

    with pytest.raises(BatchPortalProbeBlockedError):
        service.run(
            batch_id=batch.batch_id,
            dependency="Adquisiciones",
        )

def test_should_reject_non_ready_batch(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches, status=BatchStatus.CANCELLED)
    configure_credentials(credentials)
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=FakeProbe(),
    )

    with pytest.raises(BatchPortalProbeBlockedError):
        service.run(
            batch_id=batch.batch_id,
            dependency="Adquisiciones",
        )


def test_should_reject_missing_credentials(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches)
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=FakeProbe(),
    )

    with pytest.raises(BatchPortalProbeBlockedError):
        service.run(
            batch_id=batch.batch_id,
            dependency="Adquisiciones",
        )


def test_should_reject_unverified_credentials(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches)
    configure_credentials(credentials, success=False)
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=FakeProbe(),
    )

    with pytest.raises(BatchPortalProbeBlockedError):
        service.run(
            batch_id=batch.batch_id,
            dependency="Adquisiciones",
        )


def test_should_reject_expired_credential_test(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches)
    configure_credentials(
        credentials,
        tested_at=datetime.now(UTC) - timedelta(hours=25),
    )
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=FakeProbe(),
        credential_max_age_hours=24,
    )

    with pytest.raises(BatchPortalProbeBlockedError):
        service.run(
            batch_id=batch.batch_id,
            dependency="Adquisiciones",
        )


def test_should_reject_missing_cipher(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches)
    configure_credentials(credentials)
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=None,
        probe=FakeProbe(),
    )

    with pytest.raises(BatchPortalProbeConfigurationError):
        service.run(
            batch_id=batch.batch_id,
            dependency="Adquisiciones",
        )
