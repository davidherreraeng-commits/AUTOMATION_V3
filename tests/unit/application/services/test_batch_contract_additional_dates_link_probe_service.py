from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from application.ports.batch_portal_probe import (
    BatchContractAdditionalDatesLinkProbeResult,
)
from application.services.batch_portal_probe_service import (
    BatchPortalProbeService,
)
from domain.enums.batch_status import BatchStatus
from domain.enums.contractor_nature import ContractorNature
from domain.errors.batch_portal_probe_errors import (
    BatchPortalProbeBlockedError,
)
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)
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
    name = "fake-contract-additional-dates-link"

    def __init__(self) -> None:
        self.contract = None

    def probe_contract_additional_dates_link(self, *, contract, **kwargs):
        self.contract = contract
        return BatchContractAdditionalDatesLinkProbeResult(
            success=True,
            code="CONTRACT_ADDITIONAL_DATES_LINK_READY",
            message="Fechas vinculadas.",
            authenticated=True,
            assistant_opened=True,
            contract_saved_confirmed=True,
            supervisor_linked_confirmed=True,
            availability_linked_row_confirmed=True,
            budget_register_linked_confirmed=True,
            additional_dates_section_found=True,
            additional_dates_any_provided=True,
            guarantee_approval_date_provided=True,
            guarantee_approval_date_written=True,
            website_publication_date_provided=True,
            website_publication_date_written=True,
            secop_publication_date_provided=True,
            secop_publication_date_written=True,
            additional_dates_validate_clicked=True,
            additional_dates_validation_confirmed=True,
            additional_dates_link_clicked=True,
            additional_dates_success_dialog_found=True,
            additional_dates_success_dialog_accepted=True,
            additional_dates_linked_confirmed=True,
            file_reported_section_found=True,
            duration_ms=60000,
        )


def contract(*, amount: Decimal = Decimal("1")) -> ContractData:
    return ContractData(
        contract_number="90-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            nature=ContractorNature.NATURAL_PERSON,
            document_number="1042063697",
        ),
        project_code="I-23021-2026",
        object_description="Contrato de prueba C9.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=amount,
        term_days=30,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=BudgetData(
            year=2026,
            item="2111340000101501",
            subsector="Tecnología",
            cdp_code="704",
            budget_register_number="14",
            budget_register_date=date(2026, 8, 3),
            gross_total=Decimal("1"),
        ),
        supervisor=SupervisorData("52263286", "Interno"),
        secop_url="https://community.secop.gov.co/test",
        guarantee_approval_date=date(2026, 8, 3),
        website_publication_date=date(2026, 8, 3),
        secop_publication_date=date(2026, 8, 3),
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
            validation_id="e" * 32,
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


def test_should_save_and_link_additional_dates() -> None:
    current_batch, item = batch()
    fake_probe = FakeProbe()

    outcome = service(
        current_batch,
        fake_probe,
    ).run_contract_additional_dates_link(
        batch_id=current_batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation="GUARDAR SUPERVISOR CDP RP Y FECHAS 90-2026",
        allow_test_values=True,
    )

    assert fake_probe.contract == item.contract
    assert outcome.code == "CONTRACT_ADDITIONAL_DATES_LINK_READY"
    assert outcome.guarantee_approval_date == "2026-08-03"
    assert outcome.website_publication_date == "2026-08-03"
    assert outcome.secop_publication_date == "2026-08-03"
    assert outcome.additional_dates_linked_confirmed is True
    assert outcome.file_reported_section_found is True
    assert current_batch.status is BatchStatus.READY


def test_should_reject_incorrect_confirmation() -> None:
    current_batch, item = batch()

    with pytest.raises(
        BatchPortalProbeBlockedError,
        match="GUARDAR SUPERVISOR CDP RP Y FECHAS 90-2026",
    ):
        service(
            current_batch,
            FakeProbe(),
        ).run_contract_additional_dates_link(
            batch_id=current_batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="GUARDAR SUPERVISOR CDP Y RP 90-2026",
            allow_test_values=True,
        )


def test_should_require_explicit_authorization_for_test_values() -> None:
    current_batch, item = batch()

    with pytest.raises(
        BatchPortalProbeBlockedError,
        match="allow_test_values=true",
    ):
        service(
            current_batch,
            FakeProbe(),
        ).run_contract_additional_dates_link(
            batch_id=current_batch.batch_id,
            item_id=item.item_id,
            dependency="Adquisiciones",
            confirmation="GUARDAR SUPERVISOR CDP RP Y FECHAS 90-2026",
            allow_test_values=False,
        )


def test_should_preserve_optional_dates_as_none() -> None:
    current_batch, item = batch()
    object.__setattr__(item.contract, "guarantee_approval_date", None)
    object.__setattr__(item.contract, "website_publication_date", None)
    object.__setattr__(item.contract, "secop_publication_date", None)
    fake_probe = FakeProbe()
    fake_probe.probe_contract_additional_dates_link = lambda **kwargs: (
        BatchContractAdditionalDatesLinkProbeResult(
            success=True,
            code="CONTRACT_ADDITIONAL_DATES_LINK_READY",
            message="Paso omitido.",
            authenticated=True,
            assistant_opened=True,
            contract_saved_confirmed=True,
            supervisor_linked_confirmed=True,
            availability_linked_row_confirmed=True,
            budget_register_linked_confirmed=True,
            additional_dates_section_found=True,
            additional_dates_skipped=True,
            additional_dates_linked_confirmed=True,
            file_reported_section_found=True,
        )
    )

    outcome = service(
        current_batch,
        fake_probe,
    ).run_contract_additional_dates_link(
        batch_id=current_batch.batch_id,
        item_id=item.item_id,
        dependency="Adquisiciones",
        confirmation="GUARDAR SUPERVISOR CDP RP Y FECHAS 90-2026",
        allow_test_values=True,
    )

    assert outcome.guarantee_approval_date is None
    assert outcome.website_publication_date is None
    assert outcome.secop_publication_date is None
    assert outcome.additional_dates_skipped is True
