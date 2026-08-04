from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from application.dto import (
    ContractImportResult,
    ImportIssue,
)
from application.use_cases import ValidateBatch
from domain.enums import ContractorNature
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


@dataclass
class FakeContractSource:
    results: tuple[ContractImportResult, ...]

    def read(
        self,
    ) -> Iterable[ContractImportResult]:
        return iter(self.results)


def build_contract(
    *,
    contract_number: str,
    dependency: str = "Proyectos Especiales",
) -> ContractData:
    contractor = ContractorData(
        document_number="900469775-8",
        nature=ContractorNature.LEGAL_ENTITY,
    )

    supervisor = SupervisorData(
        document_number="71693738",
        supervisor_type="Supervisor",
    )

    budget = BudgetData(
        year=2026,
        item="IDEA-2026 - RECURSOS CONVENIO IDEA",
        subsector="Tecnología",
        cdp_code="235097",
        gross_total=Decimal("1476190"),
        budget_register_number="950172",
        budget_register_date=date(2026, 2, 11),
    )

    return ContractData(
        contract_number=contract_number,
        dependency=dependency,
        contractor=contractor,
        project_code="I-23021-2026",
        object_description=(
            "Servicio de software para la administración "
            "del sistema institucional."
        ),
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1476190"),
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=budget,
        supervisor=supervisor,
    )


def valid_result(
    *,
    row_number: int,
    contract_number: str,
    dependency: str = "Proyectos Especiales",
) -> ContractImportResult:
    contract = build_contract(
        contract_number=contract_number,
        dependency=dependency,
    )

    return ContractImportResult(
        row_number=row_number,
        contract=contract,
        issues=(),
        raw_data={
            "contract_number": contract_number,
            "dependency": dependency,
        },
    )


def invalid_result(
    *,
    row_number: int,
) -> ContractImportResult:
    return ContractImportResult(
        row_number=row_number,
        contract=None,
        issues=(
            ImportIssue(
                code="INVALID_VALUE",
                message=(
                    "El número del contrato es obligatorio."
                ),
                field="contract_number",
                raw_value=None,
            ),
        ),
        raw_data={
            "contract_number": None,
        },
    )


def test_should_validate_clean_batch() -> None:
    source = FakeContractSource(
        results=(
            valid_result(
                row_number=2,
                contract_number="70-2026",
            ),
            valid_result(
                row_number=3,
                contract_number="71-2026",
            ),
        )
    )

    result = ValidateBatch().execute(source)

    assert result.can_process
    assert result.total_rows == 2
    assert result.valid_count == 2
    assert result.invalid_count == 0
    assert result.batch_issues == ()

    assert tuple(
        contract.contract_number
        for contract in result.valid_contracts
    ) == (
        "70-2026",
        "71-2026",
    )


def test_should_block_batch_with_invalid_row() -> None:
    source = FakeContractSource(
        results=(
            valid_result(
                row_number=2,
                contract_number="70-2026",
            ),
            invalid_result(
                row_number=3,
            ),
        )
    )

    result = ValidateBatch().execute(source)

    assert not result.can_process
    assert result.valid_count == 1
    assert result.invalid_count == 1
    assert result.invalid_rows[0].row_number == 3


def test_should_mark_all_duplicate_occurrences_as_invalid() -> None:
    source = FakeContractSource(
        results=(
            valid_result(
                row_number=2,
                contract_number="70-2026",
            ),
            valid_result(
                row_number=3,
                contract_number="70-2026",
            ),
            valid_result(
                row_number=4,
                contract_number="71-2026",
            ),
        )
    )

    result = ValidateBatch().execute(source)

    assert not result.can_process
    assert result.has_duplicates

    assert result.valid_count == 1
    assert result.invalid_count == 2

    assert result.valid_contracts[0].contract_number == (
        "71-2026"
    )

    assert {
        row.row_number
        for row in result.invalid_rows
    } == {
        2,
        3,
    }

    for row in result.invalid_rows:
        assert row.issues[0].code == (
            "DUPLICATE_CONTRACT_IN_BATCH"
        )


def test_should_allow_same_number_in_different_dependencies() -> None:
    source = FakeContractSource(
        results=(
            valid_result(
                row_number=2,
                contract_number="70-2026",
                dependency="Proyectos Especiales",
            ),
            valid_result(
                row_number=3,
                contract_number="70-2026",
                dependency="Adquisiciones",
            ),
        )
    )

    result = ValidateBatch().execute(source)

    assert result.can_process
    assert result.valid_count == 2
    assert not result.has_duplicates


def test_should_detect_duplicates_ignoring_case_and_spaces() -> None:
    source = FakeContractSource(
        results=(
            valid_result(
                row_number=2,
                contract_number="70-2026",
                dependency="Proyectos Especiales",
            ),
            valid_result(
                row_number=3,
                contract_number=" 70-2026 ",
                dependency="proyectos   especiales",
            ),
        )
    )

    result = ValidateBatch().execute(source)

    assert not result.can_process
    assert result.has_duplicates
    assert result.valid_count == 0
    assert result.invalid_count == 2


def test_should_reject_empty_batch() -> None:
    source = FakeContractSource(
        results=()
    )

    result = ValidateBatch().execute(source)

    assert not result.can_process
    assert result.total_rows == 0
    assert result.valid_count == 0
    assert result.invalid_count == 0

    assert len(result.batch_issues) == 1
    assert result.batch_issues[0].code == "EMPTY_BATCH"