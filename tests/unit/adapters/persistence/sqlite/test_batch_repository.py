from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from adapters.persistence.sqlite.batch_repository import SQLiteBatchRepository
from domain.enums.batch_status import BatchContractStatus, BatchStatus
from domain.enums.contractor_nature import ContractorNature
from domain.errors.batch_errors import BatchAlreadyExistsError
from domain.models.budget import BudgetData
from domain.models.contract import ContractData
from domain.models.contract_batch import BatchContract, ContractBatch
from domain.models.contractor import ContractorData
from domain.models.supervisor import SupervisorData


def build_contract(number: str, dependency: str = "Adquisiciones") -> ContractData:
    return ContractData(
        contract_number=number,
        dependency=dependency,
        contractor=ContractorData(
            document_number="900469775-8",
            nature=ContractorNature.LEGAL_ENTITY,
        ),
        project_code="I-23021-2026",
        object_description="Servicio de software institucional.",
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
            budget_register_date=date(2026, 1, 22),
        ),
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Interno",
        ),
        secop_url="https://example.test/secop",
        guarantee_approval_date=date(2026, 1, 23),
        website_publication_date=date(2026, 1, 24),
        secop_publication_date=date(2026, 1, 25),
    )


def build_batch(
    *,
    validation_id: str,
    dependency: str = "Adquisiciones",
    contract_number: str = "70-2026",
    created_at: datetime | None = None,
) -> ContractBatch:
    now = created_at or datetime.now(UTC)
    return ContractBatch(
        batch_id=uuid4(),
        validation_id=validation_id,
        source_file_name="contratos.xlsx",
        dependency=dependency,
        created_by_user_id=1,
        created_by_username="operador",
        status=BatchStatus.READY,
        contracts=(
            BatchContract(
                item_id=uuid4(),
                source_row_number=2,
                contract=build_contract(contract_number, dependency),
                status=BatchContractStatus.PENDING,
            ),
        ),
        created_at=now,
        updated_at=now,
    )


def build_repository(tmp_path: Path) -> SQLiteBatchRepository:
    repository = SQLiteBatchRepository(tmp_path / "batches.sqlite3")
    repository.initialize()
    return repository


def test_should_persist_and_restore_complete_batch(tmp_path: Path) -> None:
    repository = build_repository(tmp_path)
    batch = build_batch(validation_id="a" * 32)

    stored = repository.create(batch)
    restored = repository.get_by_id(
        stored.batch_id,
        dependency="Adquisiciones",
    )

    assert restored == stored
    assert restored is not None
    assert restored.contracts[0].contract.budget.budget_register_number == "12026"
    assert restored.contracts[0].contract.secop_publication_date == date(2026, 1, 25)


def test_should_reject_second_batch_for_same_validation_dependency(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)
    repository.create(build_batch(validation_id="b" * 32))

    with pytest.raises(BatchAlreadyExistsError):
        repository.create(
            build_batch(
                validation_id="b" * 32,
                contract_number="71-2026",
            )
        )


def test_should_isolate_batch_by_dependency(tmp_path: Path) -> None:
    repository = build_repository(tmp_path)
    batch = repository.create(build_batch(validation_id="c" * 32))

    assert repository.get_by_id(
        batch.batch_id,
        dependency="Proyectos",
    ) is None
    assert repository.get_by_validation(
        "c" * 32,
        dependency="Proyectos",
    ) is None


def test_should_list_recent_batches_for_dependency(tmp_path: Path) -> None:
    repository = build_repository(tmp_path)
    now = datetime.now(UTC)
    older = repository.create(
        build_batch(
            validation_id="d" * 32,
            contract_number="72-2026",
            created_at=now - timedelta(minutes=1),
        )
    )
    newer = repository.create(
        build_batch(
            validation_id="e" * 32,
            contract_number="73-2026",
            created_at=now,
        )
    )
    repository.create(
        build_batch(
            validation_id="f" * 32,
            dependency="Proyectos",
            contract_number="74-2026",
            created_at=now + timedelta(minutes=1),
        )
    )

    listed = repository.list_by_dependency("Adquisiciones")

    assert [item.batch_id for item in listed] == [newer.batch_id, older.batch_id]
