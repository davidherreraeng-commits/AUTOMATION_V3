from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

from pydantic import BaseModel, Field

from application.dto import (
    BatchIssue,
    ContractImportResult,
    FileValidationOutcome,
    ImportIssue,
)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return str(value)


class ImportIssueResponse(BaseModel):
    code: str
    message: str
    field: str | None = None
    raw_value: Any = None

    @classmethod
    def from_issue(cls, issue: ImportIssue) -> "ImportIssueResponse":
        return cls(
            code=issue.code,
            message=issue.message,
            field=issue.field,
            raw_value=_json_safe(issue.raw_value),
        )


class BatchIssueResponse(BaseModel):
    code: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_issue(cls, issue: BatchIssue) -> "BatchIssueResponse":
        return cls(
            code=issue.code,
            message=issue.message,
            metadata=_json_safe(issue.metadata),
        )


class ValidContractRowResponse(BaseModel):
    row_number: int
    contract_number: str
    dependency: str
    contractor_document: str
    contractor_nature: str
    project_code: str
    object_description: str
    signing_date: date
    starting_date: date
    amount: Decimal
    term_days: int
    process_type: str
    procedure: str
    contract_type: str
    budget_item: str
    budget_subsector: str
    supervisor_document: str
    cdp_code: str

    @classmethod
    def from_result(
        cls,
        result: ContractImportResult,
    ) -> "ValidContractRowResponse":
        contract = result.contract
        if contract is None:
            raise ValueError("La fila no contiene un contrato válido.")

        return cls(
            row_number=result.row_number,
            contract_number=contract.contract_number,
            dependency=contract.dependency,
            contractor_document=contract.contractor.document_number,
            contractor_nature=contract.contractor.nature.value,
            project_code=contract.project_code,
            object_description=contract.object_description,
            signing_date=contract.signing_date,
            starting_date=contract.starting_date,
            amount=contract.amount,
            term_days=contract.term_days,
            process_type=contract.process_type,
            procedure=contract.procedure,
            contract_type=contract.contract_type,
            budget_item=contract.budget.item,
            budget_subsector=contract.budget.subsector,
            supervisor_document=contract.supervisor.document_number,
            cdp_code=contract.budget.cdp_code,
        )


class InvalidContractRowResponse(BaseModel):
    row_number: int
    contract_number: str | None = None
    issues: list[ImportIssueResponse]
    raw_data: dict[str, Any]

    @classmethod
    def from_result(
        cls,
        result: ContractImportResult,
    ) -> "InvalidContractRowResponse":
        raw_data = _json_safe(result.raw_data)
        contract_number = raw_data.get("contract_number")
        if contract_number is not None:
            contract_number = str(contract_number)

        return cls(
            row_number=result.row_number,
            contract_number=contract_number,
            issues=[
                ImportIssueResponse.from_issue(issue)
                for issue in result.issues
            ],
            raw_data=raw_data,
        )


class FileValidationResponse(BaseModel):
    validation_id: str
    file_name: str
    dependency: str
    sheet_name: str | None
    validated_at: datetime
    total_rows: int
    valid_count: int
    invalid_count: int
    fully_valid: bool
    can_create_batch: bool
    valid_rows: list[ValidContractRowResponse]
    invalid_rows: list[InvalidContractRowResponse]
    batch_issues: list[BatchIssueResponse]

    @classmethod
    def from_outcome(
        cls,
        outcome: FileValidationOutcome,
    ) -> "FileValidationResponse":
        validation = outcome.validation
        return cls(
            validation_id=outcome.validation_id,
            file_name=outcome.original_file_name,
            dependency=outcome.dependency,
            sheet_name=outcome.sheet_name,
            validated_at=outcome.validated_at,
            total_rows=validation.total_rows,
            valid_count=validation.valid_count,
            invalid_count=validation.invalid_count,
            fully_valid=validation.can_process,
            can_create_batch=outcome.can_create_batch,
            valid_rows=[
                ValidContractRowResponse.from_result(result)
                for result in validation.valid_rows
            ],
            invalid_rows=[
                InvalidContractRowResponse.from_result(result)
                for result in validation.invalid_rows
            ],
            batch_issues=[
                BatchIssueResponse.from_issue(issue)
                for issue in validation.batch_issues
            ],
        )
