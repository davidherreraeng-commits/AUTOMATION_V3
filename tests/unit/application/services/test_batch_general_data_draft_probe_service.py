from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from application.ports.batch_portal_probe import (
    BatchAssistantProbeResult,
    BatchGeneralDataDraftProbeResult,
    BatchHeaderDraftProbeResult,
    BatchHeaderValidationProbeResult,
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
    def __init__(self, current_batch: ContractBatch) -> None:
        self.current_batch = current_batch

    def get_by_id(self, batch_id, *, dependency: str):
        if batch_id != self.current_batch.batch_id:
            return None
        if dependency.casefold() != self.current_batch.dependency.casefold():
            return None
        return self.current_batch


class FakeCredentialRepository:
    def find_by_dependency(self, dependency: str):
        now = datetime.now(UTC)
        return PortalCredentials(
            dependency=dependency,
            portal_username="usuario.gt",
            encrypted_password="encrypted-value",
            created_at=now,
            updated_at=now,
            last_tested_at=now,
            last_test_success=True,
            last_test_code="AUTHENTICATED",
        )


class FakeCipher:
    def decrypt(self, ciphertext: str) -> str:
        return "ClavePortal2026"


class FakeProbe:
    name = "fake-general-data-draft"

    def __init__(self) -> None:
        self.contract = None

    def probe(self, **kwargs):
        return BatchPortalProbeResult(True, "READY", "Listo")

    def probe_assistant_form(self, **kwargs):
        return BatchAssistantProbeResult(True, "READY", "Listo")

    def probe_header_draft(self, **kwargs):
        return BatchHeaderDraftProbeResult(True, "READY", "Listo")

    def probe_header_validation(self, **kwargs):
        return BatchHeaderValidationProbeResult(True, "READY", "Listo")

    def probe_general_data_draft(self, *, contract, **kwargs):
        self.contract = contract
        return BatchGeneralDataDraftProbeResult(
            success=True,
            code="GENERAL_DATA_DRAFT_READY",
            message="C3 completo sin guardar.",
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
            duration_ms=9000,
        )


def contract() -> ContractData:
    return ContractData(
        contract_number="80-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.LEGAL_ENTITY,
            document_number="901398448-2",
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
            source_file_name="contracts.xlsx",
            dependency="Adquisiciones",
            created_by_user_id=1,
            created_by_username="carlos_herrera",
            status=BatchStatus.READY,
            contracts=(item,),
            created_at=now,
            updated_at=now,
        ),
        item,
    )


def service(current_batch: ContractBatch, probe: FakeProbe) -> BatchPortalProbeService:
    return BatchPortalProbeService(
        batches=FakeBatchRepository(current_batch),
        credentials=FakeCredentialRepository(),
        cipher=FakeCipher(),
        probe=probe,
    )


def test_should_map_general_data_draft_outcome() -> None:
    current_batch, item = batch()
    fake_probe = FakeProbe()

    outcome = service(current_batch, fake_probe).run_general_data_draft(
        batch_id=current_batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    assert fake_probe.contract == item.contract
    assert outcome.code == "GENERAL_DATA_DRAFT_READY"
    assert outcome.general_data_completed is True
    assert outcome.amount == "1476190"
    assert outcome.save_clicked is False


def test_should_reject_item_outside_batch() -> None:
    current_batch, _item = batch()

    with pytest.raises(BatchPortalProbeBlockedError):
        service(current_batch, FakeProbe()).run_general_data_draft(
            batch_id=current_batch.batch_id,
            item_id=uuid4(),
            dependency="Adquisiciones",
        )


def test_should_preserve_ready_batch_after_general_data_probe() -> None:
    current_batch, item = batch()

    service(current_batch, FakeProbe()).run_general_data_draft(
        batch_id=current_batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
    )

    assert current_batch.status is BatchStatus.READY
    assert item.status.value == "PENDING"
