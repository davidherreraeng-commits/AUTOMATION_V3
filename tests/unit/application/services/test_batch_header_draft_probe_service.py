from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from application.ports.batch_portal_probe import (
    BatchAssistantProbeResult,
    BatchHeaderDraftProbeResult,
    BatchPortalProbeResult,
)
from application.services.batch_portal_probe_service import BatchPortalProbeService
from domain.enums.batch_status import BatchStatus
from domain.enums.contractor_nature import ContractorNature
from domain.errors.batch_portal_probe_errors import BatchPortalProbeBlockedError
from domain.models import BudgetData, ContractData, ContractorData, SupervisorData
from domain.models.contract_batch import BatchContract, ContractBatch
from domain.models.portal_credentials import PortalCredentials


class FakeBatchRepository:
    def __init__(self, batch: ContractBatch) -> None:
        self.batch = batch

    def get_by_id(self, batch_id, *, dependency: str):
        if batch_id != self.batch.batch_id:
            return None
        if dependency.casefold() != self.batch.dependency.casefold():
            return None
        return self.batch


class FakeCredentialRepository:
    def __init__(self) -> None:
        self.credential = PortalCredentials(
            dependency="Adquisiciones",
            portal_username="usuario.gt",
            encrypted_password="encrypted-value",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_tested_at=datetime.now(UTC),
            last_test_success=True,
            last_test_code="AUTHENTICATED",
        )

    def find_by_dependency(self, dependency: str):
        return self.credential


class FakeCipher:
    def decrypt(self, ciphertext: str) -> str:
        assert ciphertext == "encrypted-value"
        return "ClavePortal2026"


class FakeProbe:
    name = "fake-header-draft"

    def __init__(self) -> None:
        self.contract: ContractData | None = None
        self.password: str | None = None

    def probe(self, **kwargs):
        return BatchPortalProbeResult(True, "READY", "Listo")

    def probe_assistant_form(self, **kwargs):
        return BatchAssistantProbeResult(True, "READY", "Listo")

    def probe_header_draft(self, *, portal_username, portal_password, contract):
        self.contract = contract
        self.password = portal_password
        return BatchHeaderDraftProbeResult(
            success=True,
            code="HEADER_DRAFT_READY",
            message="Encabezado cargado sin pulsar Validar.",
            authenticated=True,
            assistant_opened=True,
            record_type_selected=True,
            contract_number_written=True,
            contractor_dialog_opened=True,
            contractor_nature_selected=True,
            contractor_document_written=True,
            contractor_result_found=True,
            contractor_selected=True,
            project_dialog_opened=True,
            project_code_written=True,
            project_result_found=True,
            project_selected=True,
            validate_button_found=True,
            validate_clicked=False,
            duration_ms=2500,
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
        supervisor=SupervisorData("71693738", "Interno"),
        secop_url="https://community.secop.gov.co/example",
    )


def batch() -> tuple[ContractBatch, BatchContract]:
    now = datetime.now(UTC)
    item = BatchContract(
        item_id=uuid4(),
        source_row_number=2,
        contract=contract(),
    )
    return (
        ContractBatch(
            batch_id=uuid4(),
            validation_id="a" * 32,
            source_file_name="contratos.xlsx",
            dependency="Adquisiciones",
            created_by_user_id=1,
            created_by_username="jefe",
            status=BatchStatus.READY,
            contracts=(item,),
            created_at=now,
            updated_at=now,
        ),
        item,
    )


def service_for(current_batch: ContractBatch, probe: FakeProbe):
    return BatchPortalProbeService(
        batches=FakeBatchRepository(current_batch),
        credentials=FakeCredentialRepository(),
        cipher=FakeCipher(),
        probe=probe,
    )


def test_should_send_selected_batch_contract_to_safe_header_probe() -> None:
    current_batch, item = batch()
    fake_probe = FakeProbe()

    outcome = service_for(current_batch, fake_probe).run_header_draft(
        batch_id=current_batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    assert outcome.success is True
    assert outcome.item_id == item.item_id
    assert outcome.contract_number == "70-2026"
    assert outcome.contractor_document == "900469775-8"
    assert outcome.project_code == "I-23021-2026"
    assert outcome.validate_clicked is False
    assert fake_probe.contract is item.contract
    assert fake_probe.password == "ClavePortal2026"
    assert "ClavePortal2026" not in outcome.message


def test_should_reject_item_that_does_not_belong_to_batch() -> None:
    current_batch, _ = batch()

    with pytest.raises(BatchPortalProbeBlockedError):
        service_for(current_batch, FakeProbe()).run_header_draft(
            batch_id=current_batch.batch_id,
            item_id=uuid4(),
            dependency="Adquisiciones",
        )


def test_should_preserve_batch_as_ready_after_header_probe() -> None:
    current_batch, item = batch()

    service_for(current_batch, FakeProbe()).run_header_draft(
        batch_id=current_batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    assert current_batch.status is BatchStatus.READY
