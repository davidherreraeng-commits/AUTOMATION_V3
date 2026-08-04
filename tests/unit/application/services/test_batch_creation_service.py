from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from application.dto.batch_validation import BatchValidationResult
from application.dto.file_validation import FileValidationOutcome
from application.dto.import_result import ContractImportResult
from application.services.batch_creation_service import BatchCreationService
from domain.enums.contractor_nature import ContractorNature
from domain.errors.batch_errors import (
    BatchAlreadyExistsError,
    InvalidBatchSelectionError,
    StoredValidationNotFoundError,
)
from domain.models.budget import BudgetData
from domain.models.contract import ContractData
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
        ),
        supervisor=SupervisorData(document_number="71693738"),
    )


class FakeValidationStore:
    def __init__(self, outcome: FileValidationOutcome) -> None:
        self.outcome = outcome
        self.requested_dependency = None

    def validate(self, **kwargs):
        raise AssertionError("La creación de lote no debe volver a subir archivos.")

    def get_validation(self, *, validation_id: str, dependency: str):
        self.requested_dependency = dependency
        if validation_id != self.outcome.validation_id:
            raise StoredValidationNotFoundError(validation_id)
        if dependency.casefold() != self.outcome.dependency.casefold():
            raise StoredValidationNotFoundError(validation_id)
        return self.outcome


class InMemoryBatchRepository:
    def __init__(self) -> None:
        self.items = {}

    def create(self, batch):
        key = (batch.validation_id, batch.dependency.casefold())
        if key in self.items:
            raise BatchAlreadyExistsError(batch.validation_id)
        self.items[key] = batch
        return batch

    def get_by_validation(self, validation_id, *, dependency):
        return self.items.get((validation_id, dependency.casefold()))

    def get_by_id(self, batch_id: UUID, *, dependency: str):
        for batch in self.items.values():
            if batch.batch_id == batch_id and batch.dependency.casefold() == dependency.casefold():
                return batch
        return None

    def list_by_dependency(self, dependency: str, *, limit: int = 50):
        return tuple(
            batch
            for batch in self.items.values()
            if batch.dependency.casefold() == dependency.casefold()
        )[:limit]


def build_outcome() -> FileValidationOutcome:
    validation_id = "1" * 32
    return FileValidationOutcome(
        validation_id=validation_id,
        original_file_name="contratos.xlsx",
        stored_file_name="contracts.xlsx",
        dependency="Adquisiciones",
        sheet_name="Contratos",
        validated_at=datetime.now(UTC),
        validation=BatchValidationResult(
            valid_rows=(
                ContractImportResult(row_number=2, contract=build_contract("70-2026")),
                ContractImportResult(row_number=3, contract=build_contract("71-2026")),
            )
        ),
    )


def build_service():
    outcome = build_outcome()
    store = FakeValidationStore(outcome)
    repository = InMemoryBatchRepository()
    service = BatchCreationService(validations=store, batches=repository)
    return service, store, repository


def test_should_create_batch_with_only_selected_valid_rows() -> None:
    service, store, _ = build_service()

    batch = service.create(
        validation_id="1" * 32,
        selected_row_numbers=[3],
        actor_user_id=8,
        actor_username="operador",
        dependency="Adquisiciones",
    )

    assert store.requested_dependency == "Adquisiciones"
    assert batch.selected_count == 1
    assert batch.contracts[0].source_row_number == 3
    assert batch.contracts[0].contract.contract_number == "71-2026"
    assert batch.status.value == "READY"


def test_should_reject_empty_or_duplicate_selection() -> None:
    service, _, _ = build_service()

    with pytest.raises(InvalidBatchSelectionError):
        service.create(
            validation_id="1" * 32,
            selected_row_numbers=[],
            actor_user_id=8,
            actor_username="operador",
            dependency="Adquisiciones",
        )

    with pytest.raises(InvalidBatchSelectionError):
        service.create(
            validation_id="1" * 32,
            selected_row_numbers=[2, 2],
            actor_user_id=8,
            actor_username="operador",
            dependency="Adquisiciones",
        )


def test_should_reject_invalid_or_unknown_row() -> None:
    service, _, _ = build_service()

    with pytest.raises(InvalidBatchSelectionError, match="Filas rechazadas: 99"):
        service.create(
            validation_id="1" * 32,
            selected_row_numbers=[2, 99],
            actor_user_id=8,
            actor_username="operador",
            dependency="Adquisiciones",
        )


def test_should_reject_second_batch_for_same_validation() -> None:
    service, _, _ = build_service()
    payload = dict(
        validation_id="1" * 32,
        selected_row_numbers=[2],
        actor_user_id=8,
        actor_username="operador",
        dependency="Adquisiciones",
    )
    service.create(**payload)

    with pytest.raises(BatchAlreadyExistsError):
        service.create(**payload)


def test_should_not_recover_validation_from_another_dependency() -> None:
    service, _, _ = build_service()

    with pytest.raises(StoredValidationNotFoundError):
        service.create(
            validation_id="1" * 32,
            selected_row_numbers=[2],
            actor_user_id=8,
            actor_username="operador",
            dependency="Proyectos",
        )
