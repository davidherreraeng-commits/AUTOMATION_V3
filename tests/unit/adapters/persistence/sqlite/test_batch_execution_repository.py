from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.batch_repository import SQLiteBatchRepository
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.enums.contractor_nature import ContractorNature
from domain.errors.batch_execution_errors import (
    BatchExecutionInProgressError,
    BatchExecutionStateError,
)
from domain.models.budget import BudgetData
from domain.models.contract import ContractData
from domain.models.contract_batch import BatchContract, ContractBatch
from domain.models.contractor import ContractorData
from domain.models.supervisor import SupervisorData


def contract(number: str, dependency: str = "Adquisiciones") -> ContractData:
    return ContractData(
        contract_number=number,
        dependency=dependency,
        contractor=ContractorData(
            document_number="900469775-8",
            nature=ContractorNature.LEGAL_ENTITY,
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
            gross_total=Decimal("1476190"),
            budget_register_number="12026",
        ),
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Interno",
        ),
        secop_url="https://example.test/secop",
    )


def batch(validation: str, number: str = "70-2026") -> ContractBatch:
    now = datetime.now(UTC)
    return ContractBatch(
        batch_id=uuid4(),
        validation_id=validation,
        source_file_name="contratos.xlsx",
        dependency="Adquisiciones",
        created_by_user_id=1,
        created_by_username="jefe",
        status=BatchStatus.READY,
        contracts=(
            BatchContract(
                item_id=uuid4(),
                source_row_number=2,
                contract=contract(number),
            ),
        ),
        created_at=now,
        updated_at=now,
    )


def repository(tmp_path: Path) -> SQLiteBatchRepository:
    result = SQLiteBatchRepository(tmp_path / "rpa.sqlite3")
    result.initialize()
    return result


def test_should_claim_update_and_finish_batch(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    stored = repo.create(batch("a" * 32))

    claimed = repo.claim_for_processing(
        stored.batch_id,
        dependency="Adquisiciones",
    )
    assert claimed.status is BatchStatus.PROCESSING

    item = claimed.contracts[0]
    started = repo.update_contract_status(
        claimed.batch_id,
        item.item_id,
        dependency="Adquisiciones",
        status=BatchContractStatus.PROCESSING,
        message="Iniciado",
    )
    assert started.contracts[0].last_message == "Iniciado"

    repo.update_contract_status(
        claimed.batch_id,
        item.item_id,
        dependency="Adquisiciones",
        status=BatchContractStatus.COMPLETED,
        message="Finalizado",
    )
    finished = repo.finish_processing(
        claimed.batch_id,
        dependency="Adquisiciones",
        status=BatchStatus.COMPLETED,
    )

    assert finished.status is BatchStatus.COMPLETED
    assert finished.contracts[0].status is BatchContractStatus.COMPLETED
    assert finished.contracts[0].last_message == "Finalizado"


def test_should_allow_only_one_processing_batch_per_dependency(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    first = repo.create(batch("b" * 32, "71-2026"))
    second = repo.create(batch("c" * 32, "72-2026"))

    repo.claim_for_processing(first.batch_id, dependency="Adquisiciones")

    with pytest.raises(BatchExecutionInProgressError):
        repo.claim_for_processing(second.batch_id, dependency="Adquisiciones")


def test_should_reject_invalid_contract_status_transition(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    stored = repo.create(batch("d" * 32))
    claimed = repo.claim_for_processing(
        stored.batch_id,
        dependency="Adquisiciones",
    )

    with pytest.raises(BatchExecutionStateError):
        repo.update_contract_status(
            claimed.batch_id,
            claimed.contracts[0].item_id,
            dependency="Adquisiciones",
            status=BatchContractStatus.COMPLETED,
        )


def test_should_cancel_only_ready_batch(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    stored = repo.create(batch("e" * 32))

    cancelled = repo.cancel_ready(
        stored.batch_id,
        dependency="Adquisiciones",
    )
    assert cancelled.status is BatchStatus.CANCELLED

    with pytest.raises(BatchExecutionStateError):
        repo.cancel_ready(
            stored.batch_id,
            dependency="Adquisiciones",
        )
