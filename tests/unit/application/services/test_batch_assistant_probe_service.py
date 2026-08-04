from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.batch_repository import SQLiteBatchRepository
from adapters.persistence.sqlite.portal_credential_repository import (
    SQLitePortalCredentialRepository,
)
from application.ports.batch_portal_probe import (
    BatchAssistantProbeResult,
    BatchPortalProbeResult,
)
from application.services.batch_portal_probe_service import (
    BatchPortalProbeService,
)
from domain.enums.batch_status import BatchStatus
from domain.enums.contractor_nature import ContractorNature
from domain.errors.batch_portal_probe_errors import (
    BatchPortalProbeBlockedError,
    BatchPortalProbeConfigurationError,
)
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData
from domain.models.contract_batch import BatchContract, ContractBatch


class FakeCipher:
    def decrypt(self, ciphertext: str) -> str:
        assert ciphertext == "encrypted-value"
        return "ClavePortal2026"


class FakeProbe:
    name = "fake-c1-c2-probe"

    def __init__(self) -> None:
        self.password: str | None = None

    def probe(self, *, portal_username: str, portal_password: str):
        return BatchPortalProbeResult(
            success=True,
            code="NAVIGATION_READY",
            message="Navegación lista.",
        )

    def probe_assistant_form(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ):
        self.password = portal_password
        return BatchAssistantProbeResult(
            success=True,
            code="ASSISTANT_FORM_READY",
            message="Formulario disponible sin escritura.",
            authenticated=True,
            assistant_opened=True,
            assistant_container_found=True,
            record_type_found=True,
            contract_number_found=True,
            contractor_search_found=True,
            project_search_found=True,
            validate_button_found=True,
            duration_ms=1500,
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
    database = tmp_path / "db.sqlite3"
    batches = SQLiteBatchRepository(database)
    batches.initialize()
    credentials = SQLitePortalCredentialRepository(database)
    credentials.initialize()
    return batches, credentials


def create_batch(batches: SQLiteBatchRepository) -> ContractBatch:
    now = datetime.now(UTC)
    return batches.create(
        ContractBatch(
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
    )


def configure_credentials(
    credentials: SQLitePortalCredentialRepository,
) -> None:
    credentials.upsert(
        dependency="Adquisiciones",
        portal_username="usuario.gt",
        encrypted_password="encrypted-value",
    )
    credentials.record_test_result(
        dependency="Adquisiciones",
        tested_at=datetime.now(UTC),
        success=True,
        code="AUTHENTICATED",
    )


def test_should_return_safe_c1_c2_outcome(tmp_path: Path) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches)
    configure_credentials(credentials)
    probe = FakeProbe()
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=probe,
    )

    outcome = service.run_assistant_form(
        batch_id=batch.batch_id,
        dependency="Adquisiciones",
    )

    assert outcome.success is True
    assert outcome.code == "ASSISTANT_FORM_READY"
    assert outcome.assistant_opened is True
    assert outcome.validate_button_found is True
    assert outcome.missing_controls == ()
    assert probe.password == "ClavePortal2026"
    assert "ClavePortal2026" not in outcome.message


def test_should_reject_c1_c2_probe_without_cipher(tmp_path: Path) -> None:
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
        service.run_assistant_form(
            batch_id=batch.batch_id,
            dependency="Adquisiciones",
        )


def test_should_reject_c1_c2_probe_for_non_ready_batch(
    tmp_path: Path,
) -> None:
    batches, credentials = repositories(tmp_path)
    batch = create_batch(batches)
    batches.cancel_ready(
        batch.batch_id,
        dependency="Adquisiciones",
    )
    configure_credentials(credentials)
    service = BatchPortalProbeService(
        batches=batches,
        credentials=credentials,
        cipher=FakeCipher(),
        probe=FakeProbe(),
    )

    with pytest.raises(BatchPortalProbeBlockedError):
        service.run_assistant_form(
            batch_id=batch.batch_id,
            dependency="Adquisiciones",
        )
