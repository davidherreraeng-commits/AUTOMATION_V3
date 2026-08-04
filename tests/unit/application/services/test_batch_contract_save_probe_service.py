from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from application.ports.batch_portal_probe import BatchContractSaveProbeResult
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
    name = "fake-contract-save"

    def __init__(self) -> None:
        self.contract = None

    def probe_contract_save(self, *, contract, **kwargs):
        self.contract = contract
        return BatchContractSaveProbeResult(
            success=True,
            code="CONTRACT_SAVE_READY",
            message="Contrato guardado.",
            authenticated=True,
            assistant_opened=True,
            header_validation_confirmed=True,
            general_data_completed=True,
            general_completion_completed=True,
            general_validation_confirmed=True,
            save_button_found=True,
            save_clicked=True,
            success_dialog_found=True,
            success_dialog_accepted=True,
            contract_saved_confirmed=True,
            supervisor_section_found=True,
            duration_ms=20000,
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
        object_description="Contrato de prueba.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1"),
        term_days=30,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="IDEA-2026",
            subsector="Tecnología",
            cdp_code="235097",
            budget_register_number="950172",
            gross_total=Decimal("1"),
        ),
        supervisor=SupervisorData("71693738", "Interno"),
        secop_url="https://community.secop.gov.co/test",
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
            validation_id="b" * 32,
            source_file_name="test.xlsx",
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


def service(current_batch: ContractBatch, fake_probe: FakeProbe):
    return BatchPortalProbeService(
        batches=FakeBatchRepository(current_batch),
        credentials=FakeCredentialRepository(),
        cipher=FakeCipher(),
        probe=fake_probe,
    )


def test_should_save_test_contract_with_exact_confirmation() -> None:
    current_batch, item = batch()
    fake_probe = FakeProbe()

    outcome = service(current_batch, fake_probe).run_contract_save(
        batch_id=current_batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation="GUARDAR 80-2026",
        allow_test_values=True,
    )

    assert fake_probe.contract == item.contract
    assert outcome.code == "CONTRACT_SAVE_READY"
    assert outcome.amount == "1"
    assert outcome.save_clicked is True
    assert outcome.supervisor_section_found is True
    assert current_batch.status is BatchStatus.READY


def test_should_reject_incorrect_save_confirmation() -> None:
    current_batch, item = batch()

    with pytest.raises(BatchPortalProbeBlockedError, match="GUARDAR 80-2026"):
        service(current_batch, FakeProbe()).run_contract_save(
            batch_id=current_batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="GUARDAR",
            allow_test_values=True,
        )


def test_should_require_explicit_test_value_authorization() -> None:
    current_batch, item = batch()

    with pytest.raises(BatchPortalProbeBlockedError, match="allow_test_values"):
        service(current_batch, FakeProbe()).run_contract_save(
            batch_id=current_batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="GUARDAR 80-2026",
            allow_test_values=False,
        )
