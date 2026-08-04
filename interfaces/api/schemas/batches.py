from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from application.dto.batch_execution import BatchExecutionPreflight
from application.dto.batch_portal_probe import (
    BatchAssistantProbeOutcome,
    BatchContractSaveProbeOutcome,
    BatchContractAvailabilityLinkProbeOutcome,
    BatchContractBudgetRegisterLinkProbeOutcome,
    BatchContractAdditionalDatesLinkProbeOutcome,
    BatchContractSupervisorLinkProbeOutcome,
    BatchGeneralCompletionDraftProbeOutcome,
    BatchGeneralDataDraftProbeOutcome,
    BatchGeneralValidationProbeOutcome,
    BatchHeaderDraftProbeOutcome,
    BatchHeaderValidationProbeOutcome,
    BatchPortalProbeOutcome,
)
from domain.models.contract_batch import BatchContract, ContractBatch


class BatchCreateRequest(BaseModel):
    validation_id: str = Field(min_length=32, max_length=32)
    selected_row_numbers: list[int] = Field(min_length=1, max_length=5000)

    @field_validator("validation_id")
    @classmethod
    def normalize_validation_id(cls, value: str) -> str:
        normalized = str(value).strip().casefold()
        if any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("El identificador de validación no es válido.")
        return normalized

    @field_validator("selected_row_numbers")
    @classmethod
    def validate_selected_rows(cls, value: list[int]) -> list[int]:
        normalized = [int(row) for row in value]
        if any(row < 2 for row in normalized):
            raise ValueError("Las filas seleccionadas deben ser iguales o superiores a 2.")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Las filas seleccionadas no pueden repetirse.")
        return normalized


class BatchHeaderDraftProbeRequest(BaseModel):
    item_id: UUID


class BatchHeaderValidationProbeRequest(BaseModel):
    item_id: UUID


class BatchGeneralDataDraftProbeRequest(BaseModel):
    item_id: UUID


class BatchGeneralCompletionDraftProbeRequest(BaseModel):
    item_id: UUID


class BatchGeneralValidationProbeRequest(BaseModel):
    item_id: UUID


class BatchContractSaveProbeRequest(BaseModel):
    item_id: UUID
    confirmation: str = Field(min_length=1, max_length=120)
    allow_test_values: bool = False

    @field_validator("confirmation")
    @classmethod
    def normalize_confirmation(cls, value: str) -> str:
        normalized = " ".join(str(value).strip().split())
        if not normalized:
            raise ValueError("La confirmación es obligatoria.")
        return normalized


class BatchContractSupervisorLinkProbeRequest(BaseModel):
    item_id: UUID
    confirmation: str = Field(min_length=1, max_length=160)
    allow_test_values: bool = False

    @field_validator("confirmation")
    @classmethod
    def normalize_confirmation(cls, value: str) -> str:
        normalized = " ".join(str(value).strip().split())
        if not normalized:
            raise ValueError("La confirmación es obligatoria.")
        return normalized


class BatchContractAvailabilityLinkProbeRequest(BaseModel):
    item_id: UUID
    confirmation: str = Field(min_length=1, max_length=180)
    allow_test_values: bool = False

    @field_validator("confirmation")
    @classmethod
    def normalize_confirmation(cls, value: str) -> str:
        normalized = " ".join(str(value).strip().split())
        if not normalized:
            raise ValueError("La confirmación es obligatoria.")
        return normalized


class BatchContractBudgetRegisterLinkProbeRequest(BaseModel):
    item_id: UUID
    confirmation: str = Field(min_length=1, max_length=200)
    allow_test_values: bool = False

    @field_validator("confirmation")
    @classmethod
    def normalize_confirmation(cls, value: str) -> str:
        normalized = " ".join(str(value).strip().split())
        if not normalized:
            raise ValueError("La confirmación es obligatoria.")
        return normalized


class BatchContractAdditionalDatesLinkProbeRequest(BaseModel):
    item_id: UUID
    confirmation: str = Field(min_length=1, max_length=220)
    allow_test_values: bool = False

    @field_validator("confirmation")
    @classmethod
    def normalize_confirmation(cls, value: str) -> str:
        normalized = " ".join(str(value).strip().split())
        if not normalized:
            raise ValueError("La confirmación es obligatoria.")
        return normalized


class BatchContractResponse(BaseModel):
    item_id: UUID
    row_number: int
    contract_number: str
    contractor_document: str
    project_code: str
    amount: Decimal
    status: str
    last_message: str | None = None

    @classmethod
    def from_domain(cls, item: BatchContract) -> "BatchContractResponse":
        return cls(
            item_id=item.item_id,
            row_number=item.source_row_number,
            contract_number=item.contract.contract_number,
            contractor_document=item.contract.contractor.document_number,
            project_code=item.contract.project_code,
            amount=item.contract.amount,
            status=item.status.value,
            last_message=item.last_message,
        )


class BatchResponse(BaseModel):
    batch_id: UUID
    validation_id: str
    source_file_name: str
    dependency: str
    created_by_user_id: int
    created_by_username: str
    status: str
    selected_count: int
    created_at: datetime
    updated_at: datetime
    contracts: list[BatchContractResponse]

    @classmethod
    def from_domain(cls, batch: ContractBatch) -> "BatchResponse":
        return cls(
            batch_id=batch.batch_id,
            validation_id=batch.validation_id,
            source_file_name=batch.source_file_name,
            dependency=batch.dependency,
            created_by_user_id=batch.created_by_user_id,
            created_by_username=batch.created_by_username,
            status=batch.status.value,
            selected_count=batch.selected_count,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
            contracts=[
                BatchContractResponse.from_domain(item)
                for item in batch.contracts
            ],
        )


class BatchListResponse(BaseModel):
    total: int
    items: list[BatchResponse]

    @classmethod
    def from_domain(
        cls,
        batches: tuple[ContractBatch, ...],
    ) -> "BatchListResponse":
        items = [BatchResponse.from_domain(batch) for batch in batches]
        return cls(total=len(items), items=items)


class BatchExecutionIssueResponse(BaseModel):
    code: str
    message: str
    blocking: bool


class BatchExecutionPreflightResponse(BaseModel):
    batch_id: UUID
    batch_status: str
    dependency: str
    runner_name: str
    execution_enabled: bool
    runner_available: bool
    credentials_configured: bool
    credentials_recently_tested: bool
    active_batch_id: UUID | None
    checked_at: datetime
    can_execute: bool
    issues: list[BatchExecutionIssueResponse]

    @classmethod
    def from_domain(
        cls,
        preflight: BatchExecutionPreflight,
    ) -> "BatchExecutionPreflightResponse":
        return cls(
            batch_id=preflight.batch_id,
            batch_status=preflight.batch_status.value,
            dependency=preflight.dependency,
            runner_name=preflight.runner_name,
            execution_enabled=preflight.execution_enabled,
            runner_available=preflight.runner_available,
            credentials_configured=preflight.credentials_configured,
            credentials_recently_tested=(
                preflight.credentials_recently_tested
            ),
            active_batch_id=preflight.active_batch_id,
            checked_at=preflight.checked_at,
            can_execute=preflight.can_execute,
            issues=[
                BatchExecutionIssueResponse(
                    code=issue.code,
                    message=issue.message,
                    blocking=issue.blocking,
                )
                for issue in preflight.issues
            ],
        )


class BatchExecutionStatusResponse(BaseModel):
    active_in_process: bool
    pending_count: int
    processing_count: int
    completed_count: int
    failed_count: int
    manual_review_count: int
    batch: BatchResponse

    @classmethod
    def from_domain(
        cls,
        batch: ContractBatch,
        *,
        active_in_process: bool,
    ) -> "BatchExecutionStatusResponse":
        counts = {
            "PENDING": 0,
            "PROCESSING": 0,
            "COMPLETED": 0,
            "FAILED": 0,
            "MANUAL_REVIEW": 0,
        }
        for item in batch.contracts:
            counts[item.status.value] += 1
        return cls(
            active_in_process=active_in_process,
            pending_count=counts["PENDING"],
            processing_count=counts["PROCESSING"],
            completed_count=counts["COMPLETED"],
            failed_count=counts["FAILED"],
            manual_review_count=counts["MANUAL_REVIEW"],
            batch=BatchResponse.from_domain(batch),
        )


class BatchPortalProbeResponse(BaseModel):
    batch_id: UUID
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    authenticated: bool
    contracting_menu_found: bool
    enter_contract_found: bool
    assistant_access_found: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchPortalProbeOutcome,
    ) -> "BatchPortalProbeResponse":
        return cls(
            batch_id=outcome.batch_id,
            dependency=outcome.dependency,
            probe_name=outcome.probe_name,
            success=outcome.success,
            code=outcome.code,
            message=outcome.message,
            authenticated=outcome.authenticated,
            contracting_menu_found=outcome.contracting_menu_found,
            enter_contract_found=outcome.enter_contract_found,
            assistant_access_found=outcome.assistant_access_found,
            duration_ms=outcome.duration_ms,
            checked_at=outcome.checked_at,
        )

class BatchAssistantProbeResponse(BaseModel):
    batch_id: UUID
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    authenticated: bool
    assistant_opened: bool
    assistant_container_found: bool
    record_type_found: bool
    contract_number_found: bool
    contractor_search_found: bool
    project_search_found: bool
    validate_button_found: bool
    missing_controls: list[str]
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchAssistantProbeOutcome,
    ) -> "BatchAssistantProbeResponse":
        return cls(
            batch_id=outcome.batch_id,
            dependency=outcome.dependency,
            probe_name=outcome.probe_name,
            success=outcome.success,
            code=outcome.code,
            message=outcome.message,
            authenticated=outcome.authenticated,
            assistant_opened=outcome.assistant_opened,
            assistant_container_found=outcome.assistant_container_found,
            record_type_found=outcome.record_type_found,
            contract_number_found=outcome.contract_number_found,
            contractor_search_found=outcome.contractor_search_found,
            project_search_found=outcome.project_search_found,
            validate_button_found=outcome.validate_button_found,
            missing_controls=list(outcome.missing_controls),
            duration_ms=outcome.duration_ms,
            checked_at=outcome.checked_at,
        )



class BatchHeaderDraftProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    contractor_document: str
    contractor_nature: str
    project_code: str
    authenticated: bool
    assistant_opened: bool
    record_type_selected: bool
    contract_number_written: bool
    contractor_dialog_opened: bool
    contractor_nature_selected: bool
    contractor_document_written: bool
    contractor_result_found: bool
    contractor_selected: bool
    project_dialog_opened: bool
    project_code_written: bool
    project_result_found: bool
    project_selected: bool
    validate_button_found: bool
    validate_clicked: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchHeaderDraftProbeOutcome,
    ) -> "BatchHeaderDraftProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })

class BatchGeneralDataDraftProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    contractor_document: str
    contractor_nature: str
    project_code: str
    object_description: str
    signing_date: str
    starting_date: str
    amount: str
    term_days: int
    process_type: str
    procedure: str
    contract_type: str
    authenticated: bool
    assistant_opened: bool
    header_validation_confirmed: bool
    object_written: bool
    signing_date_written: bool
    starting_date_written: bool
    amount_written: bool
    amount_in_words_generated: bool
    contract_term_written: bool
    term_unit_days_selected: bool
    process_type_selected: bool
    procedure_selected: bool
    contract_type_selected: bool
    other_currency_no_selected: bool
    general_data_completed: bool
    general_validate_clicked: bool
    save_clicked: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchGeneralDataDraftProbeOutcome,
    ) -> "BatchGeneralDataDraftProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })


class BatchGeneralCompletionDraftProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    contractor_document: str
    contractor_nature: str
    project_code: str
    budget_year: int
    budget_item: str
    budget_subsector: str
    secop_url: str
    execution_department: str
    execution_city: str
    authenticated: bool
    assistant_opened: bool
    header_validation_confirmed: bool
    general_data_completed: bool
    government_plan_selected: bool
    budget_year_selected: bool
    budget_item_selected: bool
    budget_subsector_selected: bool
    budget_link_clicked: bool
    secop_yes_selected: bool
    secop_url_written: bool
    advance_no_selected: bool
    commercial_trust_no_selected: bool
    urgency_no_selected: bool
    future_commitment_no_selected: bool
    cooperation_contract_no_selected: bool
    execution_department_selected: bool
    execution_city_selected: bool
    final_validate_button_found: bool
    general_completion_completed: bool
    general_validate_clicked: bool
    save_clicked: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchGeneralCompletionDraftProbeOutcome,
    ) -> "BatchGeneralCompletionDraftProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })


class BatchGeneralValidationProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    contractor_document: str
    contractor_nature: str
    project_code: str
    authenticated: bool
    assistant_opened: bool
    header_validation_confirmed: bool
    general_data_completed: bool
    general_completion_completed: bool
    final_validate_button_found: bool
    general_validate_clicked: bool
    general_validation_confirmed: bool
    save_button_found: bool
    save_clicked: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchGeneralValidationProbeOutcome,
    ) -> "BatchGeneralValidationProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })


class BatchContractSaveProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    contractor_document: str
    contractor_nature: str
    project_code: str
    amount: str
    authenticated: bool
    assistant_opened: bool
    header_validation_confirmed: bool
    general_data_completed: bool
    general_completion_completed: bool
    general_validation_confirmed: bool
    save_button_found: bool
    save_clicked: bool
    success_dialog_found: bool
    success_dialog_accepted: bool
    contract_saved_confirmed: bool
    supervisor_section_found: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchContractSaveProbeOutcome,
    ) -> "BatchContractSaveProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })


class BatchContractSupervisorLinkProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    supervisor_document: str
    supervisor_type: str
    amount: str
    authenticated: bool
    assistant_opened: bool
    contract_saved_confirmed: bool
    supervisor_section_found: bool
    supervisor_dialog_opened: bool
    supervisor_nature_selected: bool
    supervisor_id_type_selected: bool
    supervisor_document_written: bool
    supervisor_result_found: bool
    supervisor_selected: bool
    supervisor_type_internal_confirmed: bool
    supervisor_validate_clicked: bool
    supervisor_validation_confirmed: bool
    supervisor_link_clicked: bool
    success_dialog_found: bool
    success_dialog_accepted: bool
    supervisor_linked_confirmed: bool
    availability_section_found: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchContractSupervisorLinkProbeOutcome,
    ) -> "BatchContractSupervisorLinkProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })


class BatchContractAvailabilityLinkProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    supervisor_document: str
    supervisor_type: str
    cdp_code: str
    amount: str
    authenticated: bool
    assistant_opened: bool
    contract_saved_confirmed: bool
    supervisor_section_found: bool
    supervisor_dialog_opened: bool
    supervisor_nature_selected: bool
    supervisor_id_type_selected: bool
    supervisor_document_written: bool
    supervisor_result_found: bool
    supervisor_selected: bool
    supervisor_type_internal_confirmed: bool
    supervisor_validate_clicked: bool
    supervisor_validation_confirmed: bool
    supervisor_link_clicked: bool
    supervisor_success_dialog_found: bool
    supervisor_success_dialog_accepted: bool
    supervisor_linked_confirmed: bool
    availability_section_found: bool
    availability_search_written: bool
    availability_result_found: bool
    availability_result_matches: bool
    availability_link_clicked: bool
    availability_link_success_found: bool
    availability_linked_row_confirmed: bool
    continue_button_found: bool
    continue_clicked: bool
    budget_register_section_found: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchContractAvailabilityLinkProbeOutcome,
    ) -> "BatchContractAvailabilityLinkProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })


class BatchContractBudgetRegisterLinkProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    supervisor_document: str
    cdp_code: str
    budget_register_number: str
    budget_register_date: str | None
    gross_total: str
    amount: str
    authenticated: bool
    assistant_opened: bool
    contract_saved_confirmed: bool
    supervisor_linked_confirmed: bool
    availability_linked_row_confirmed: bool
    budget_register_section_found: bool
    budget_register_number_written: bool
    budget_register_date_provided: bool
    budget_register_date_written: bool
    budget_register_availability_selected: bool
    gross_total_written: bool
    budget_register_validate_clicked: bool
    budget_register_validation_confirmed: bool
    budget_register_link_clicked: bool
    budget_register_success_dialog_found: bool
    budget_register_success_dialog_accepted: bool
    budget_register_linked_confirmed: bool
    additional_dates_section_found: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchContractBudgetRegisterLinkProbeOutcome,
    ) -> "BatchContractBudgetRegisterLinkProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })


class BatchContractAdditionalDatesLinkProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    cdp_code: str
    budget_register_number: str
    guarantee_approval_date: str | None
    website_publication_date: str | None
    secop_publication_date: str | None
    amount: str
    authenticated: bool
    assistant_opened: bool
    contract_saved_confirmed: bool
    supervisor_linked_confirmed: bool
    availability_linked_row_confirmed: bool
    budget_register_linked_confirmed: bool
    additional_dates_section_found: bool
    additional_dates_any_provided: bool
    guarantee_approval_date_provided: bool
    guarantee_approval_date_written: bool
    website_publication_date_provided: bool
    website_publication_date_written: bool
    secop_publication_date_provided: bool
    secop_publication_date_written: bool
    additional_dates_validate_clicked: bool
    additional_dates_validation_confirmed: bool
    additional_dates_link_clicked: bool
    additional_dates_success_dialog_found: bool
    additional_dates_success_dialog_accepted: bool
    additional_dates_skipped: bool
    additional_dates_linked_confirmed: bool
    file_reported_section_found: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchContractAdditionalDatesLinkProbeOutcome,
    ) -> "BatchContractAdditionalDatesLinkProbeResponse":
        return cls(**{
            field: getattr(outcome, field)
            for field in cls.model_fields
        })


class BatchHeaderValidationProbeResponse(BaseModel):
    batch_id: UUID
    item_id: UUID
    row_number: int
    dependency: str
    probe_name: str
    success: bool
    code: str
    message: str
    contract_number: str
    contractor_document: str
    contractor_nature: str
    project_code: str
    authenticated: bool
    assistant_opened: bool
    record_type_selected: bool
    contract_number_written: bool
    contractor_selected: bool
    project_selected: bool
    validate_button_found: bool
    validate_clicked: bool
    header_validation_confirmed: bool
    general_data_ready: bool
    general_object_found: bool
    general_signing_date_found: bool
    general_starting_date_found: bool
    general_amount_found: bool
    general_contract_term_found: bool
    missing_controls: list[str]
    save_clicked: bool
    duration_ms: int
    checked_at: datetime

    @classmethod
    def from_domain(
        cls,
        outcome: BatchHeaderValidationProbeOutcome,
    ) -> "BatchHeaderValidationProbeResponse":
        data = {
            field: getattr(outcome, field)
            for field in cls.model_fields
        }
        data["missing_controls"] = list(outcome.missing_controls)
        return cls(**data)

