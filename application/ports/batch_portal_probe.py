from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.models.contract import ContractData


@dataclass(frozen=True, slots=True)
class BatchPortalProbeResult:
    """Resultado seguro de una comprobación de navegación del portal."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    contracting_menu_found: bool = False
    enter_contract_found: bool = False
    assistant_access_found: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "success", bool(self.success))
        object.__setattr__(self, "authenticated", bool(self.authenticated))
        object.__setattr__(
            self,
            "contracting_menu_found",
            bool(self.contracting_menu_found),
        )
        object.__setattr__(
            self,
            "enter_contract_found",
            bool(self.enter_contract_found),
        )
        object.__setattr__(
            self,
            "assistant_access_found",
            bool(self.assistant_access_found),
        )


@dataclass(frozen=True, slots=True)
class BatchAssistantProbeResult:
    """Resultado del diagnóstico C1-C2 sin completar ni validar datos."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    assistant_container_found: bool = False
    record_type_found: bool = False
    contract_number_found: bool = False
    contractor_search_found: bool = False
    project_search_found: bool = False
    validate_button_found: bool = False
    missing_controls: tuple[str, ...] = ()
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        missing = tuple(
            item
            for item in (
                str(value).strip()
                for value in self.missing_controls
            )
            if item
        )
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "success", bool(self.success))
        object.__setattr__(self, "authenticated", bool(self.authenticated))
        object.__setattr__(self, "assistant_opened", bool(self.assistant_opened))
        object.__setattr__(
            self,
            "assistant_container_found",
            bool(self.assistant_container_found),
        )
        object.__setattr__(
            self,
            "record_type_found",
            bool(self.record_type_found),
        )
        object.__setattr__(
            self,
            "contract_number_found",
            bool(self.contract_number_found),
        )
        object.__setattr__(
            self,
            "contractor_search_found",
            bool(self.contractor_search_found),
        )
        object.__setattr__(
            self,
            "project_search_found",
            bool(self.project_search_found),
        )
        object.__setattr__(
            self,
            "validate_button_found",
            bool(self.validate_button_found),
        )
        object.__setattr__(self, "missing_controls", missing)


@dataclass(frozen=True, slots=True)
class BatchHeaderDraftProbeResult:
    """Resultado de completar C1-C2 sin pulsar Validar ni guardar."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    record_type_selected: bool = False
    contract_number_written: bool = False
    contractor_dialog_opened: bool = False
    contractor_nature_selected: bool = False
    contractor_document_written: bool = False
    contractor_result_found: bool = False
    contractor_selected: bool = False
    project_dialog_opened: bool = False
    project_code_written: bool = False
    project_result_found: bool = False
    project_selected: bool = False
    validate_button_found: bool = False
    validate_clicked: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "record_type_selected",
            "contract_number_written",
            "contractor_dialog_opened",
            "contractor_nature_selected",
            "contractor_document_written",
            "contractor_result_found",
            "contractor_selected",
            "project_dialog_opened",
            "project_code_written",
            "project_result_found",
            "project_selected",
            "validate_button_found",
            "validate_clicked",
        ):
            object.__setattr__(self, field_name, bool(getattr(self, field_name)))


@dataclass(frozen=True, slots=True)
class BatchHeaderValidationProbeResult:
    """Resultado de validar C1-C2 y comprobar C3 sin guardar."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    record_type_selected: bool = False
    contract_number_written: bool = False
    contractor_selected: bool = False
    project_selected: bool = False
    validate_button_found: bool = False
    validate_clicked: bool = False
    header_validation_confirmed: bool = False
    general_data_ready: bool = False
    general_object_found: bool = False
    general_signing_date_found: bool = False
    general_starting_date_found: bool = False
    general_amount_found: bool = False
    general_contract_term_found: bool = False
    missing_controls: tuple[str, ...] = ()
    save_clicked: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        missing = tuple(
            item
            for item in (
                str(value).strip()
                for value in self.missing_controls
            )
            if item
        )
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "missing_controls", missing)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "record_type_selected",
            "contract_number_written",
            "contractor_selected",
            "project_selected",
            "validate_button_found",
            "validate_clicked",
            "header_validation_confirmed",
            "general_data_ready",
            "general_object_found",
            "general_signing_date_found",
            "general_starting_date_found",
            "general_amount_found",
            "general_contract_term_found",
            "save_clicked",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class BatchGeneralDataDraftProbeResult:
    """Resultado de completar C3 sin validar ni guardar el contrato."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    header_validation_confirmed: bool = False
    object_written: bool = False
    signing_date_written: bool = False
    starting_date_written: bool = False
    amount_written: bool = False
    amount_in_words_generated: bool = False
    contract_term_written: bool = False
    term_unit_days_selected: bool = False
    process_type_selected: bool = False
    procedure_selected: bool = False
    contract_type_selected: bool = False
    other_currency_no_selected: bool = False
    general_data_completed: bool = False
    general_validate_clicked: bool = False
    save_clicked: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "header_validation_confirmed",
            "object_written",
            "signing_date_written",
            "starting_date_written",
            "amount_written",
            "amount_in_words_generated",
            "contract_term_written",
            "term_unit_days_selected",
            "process_type_selected",
            "procedure_selected",
            "contract_type_selected",
            "other_currency_no_selected",
            "general_data_completed",
            "general_validate_clicked",
            "save_clicked",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class BatchGeneralCompletionDraftProbeResult:
    """Resultado de completar C4 sin validar ni guardar el contrato."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    header_validation_confirmed: bool = False
    general_data_completed: bool = False
    government_plan_selected: bool = False
    budget_year_selected: bool = False
    budget_item_selected: bool = False
    budget_subsector_selected: bool = False
    budget_link_clicked: bool = False
    secop_yes_selected: bool = False
    secop_url_written: bool = False
    advance_no_selected: bool = False
    commercial_trust_no_selected: bool = False
    urgency_no_selected: bool = False
    future_commitment_no_selected: bool = False
    cooperation_contract_no_selected: bool = False
    execution_department_selected: bool = False
    execution_city_selected: bool = False
    final_validate_button_found: bool = False
    general_completion_completed: bool = False
    general_validate_clicked: bool = False
    save_clicked: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "header_validation_confirmed",
            "general_data_completed",
            "government_plan_selected",
            "budget_year_selected",
            "budget_item_selected",
            "budget_subsector_selected",
            "budget_link_clicked",
            "secop_yes_selected",
            "secop_url_written",
            "advance_no_selected",
            "commercial_trust_no_selected",
            "urgency_no_selected",
            "future_commitment_no_selected",
            "cooperation_contract_no_selected",
            "execution_department_selected",
            "execution_city_selected",
            "final_validate_button_found",
            "general_completion_completed",
            "general_validate_clicked",
            "save_clicked",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class BatchGeneralValidationProbeResult:
    """Resultado de validar C3-C4 sin pulsar Guardar."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    header_validation_confirmed: bool = False
    general_data_completed: bool = False
    general_completion_completed: bool = False
    final_validate_button_found: bool = False
    general_validate_clicked: bool = False
    general_validation_confirmed: bool = False
    save_button_found: bool = False
    save_clicked: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "header_validation_confirmed",
            "general_data_completed",
            "general_completion_completed",
            "final_validate_button_found",
            "general_validate_clicked",
            "general_validation_confirmed",
            "save_button_found",
            "save_clicked",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class BatchContractSaveProbeResult:
    """Resultado de guardar un contrato de prueba y abrir supervisor."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    header_validation_confirmed: bool = False
    general_data_completed: bool = False
    general_completion_completed: bool = False
    general_validation_confirmed: bool = False
    save_button_found: bool = False
    save_clicked: bool = False
    success_dialog_found: bool = False
    success_dialog_accepted: bool = False
    contract_saved_confirmed: bool = False
    supervisor_section_found: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "header_validation_confirmed",
            "general_data_completed",
            "general_completion_completed",
            "general_validation_confirmed",
            "save_button_found",
            "save_clicked",
            "success_dialog_found",
            "success_dialog_accepted",
            "contract_saved_confirmed",
            "supervisor_section_found",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class BatchContractSupervisorLinkProbeResult:
    """Resultado de guardar un contrato y vincular su supervisor interno."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    contract_saved_confirmed: bool = False
    supervisor_section_found: bool = False
    supervisor_dialog_opened: bool = False
    supervisor_nature_selected: bool = False
    supervisor_id_type_selected: bool = False
    supervisor_document_written: bool = False
    supervisor_result_found: bool = False
    supervisor_selected: bool = False
    supervisor_type_internal_confirmed: bool = False
    supervisor_validate_clicked: bool = False
    supervisor_validation_confirmed: bool = False
    supervisor_link_clicked: bool = False
    success_dialog_found: bool = False
    success_dialog_accepted: bool = False
    supervisor_linked_confirmed: bool = False
    availability_section_found: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "contract_saved_confirmed",
            "supervisor_section_found",
            "supervisor_dialog_opened",
            "supervisor_nature_selected",
            "supervisor_id_type_selected",
            "supervisor_document_written",
            "supervisor_result_found",
            "supervisor_selected",
            "supervisor_type_internal_confirmed",
            "supervisor_validate_clicked",
            "supervisor_validation_confirmed",
            "supervisor_link_clicked",
            "success_dialog_found",
            "success_dialog_accepted",
            "supervisor_linked_confirmed",
            "availability_section_found",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class BatchContractAvailabilityLinkProbeResult:
    """Resultado de guardar, vincular supervisor y CDP controladamente."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    contract_saved_confirmed: bool = False
    supervisor_section_found: bool = False
    supervisor_dialog_opened: bool = False
    supervisor_nature_selected: bool = False
    supervisor_id_type_selected: bool = False
    supervisor_document_written: bool = False
    supervisor_result_found: bool = False
    supervisor_selected: bool = False
    supervisor_type_internal_confirmed: bool = False
    supervisor_validate_clicked: bool = False
    supervisor_validation_confirmed: bool = False
    supervisor_link_clicked: bool = False
    supervisor_success_dialog_found: bool = False
    supervisor_success_dialog_accepted: bool = False
    supervisor_linked_confirmed: bool = False
    availability_section_found: bool = False
    availability_search_written: bool = False
    availability_result_found: bool = False
    availability_result_matches: bool = False
    availability_link_clicked: bool = False
    availability_link_success_found: bool = False
    availability_linked_row_confirmed: bool = False
    continue_button_found: bool = False
    continue_clicked: bool = False
    budget_register_section_found: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "contract_saved_confirmed",
            "supervisor_section_found",
            "supervisor_dialog_opened",
            "supervisor_nature_selected",
            "supervisor_id_type_selected",
            "supervisor_document_written",
            "supervisor_result_found",
            "supervisor_selected",
            "supervisor_type_internal_confirmed",
            "supervisor_validate_clicked",
            "supervisor_validation_confirmed",
            "supervisor_link_clicked",
            "supervisor_success_dialog_found",
            "supervisor_success_dialog_accepted",
            "supervisor_linked_confirmed",
            "availability_section_found",
            "availability_search_written",
            "availability_result_found",
            "availability_result_matches",
            "availability_link_clicked",
            "availability_link_success_found",
            "availability_linked_row_confirmed",
            "continue_button_found",
            "continue_clicked",
            "budget_register_section_found",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class BatchContractBudgetRegisterLinkProbeResult:
    """Resultado de guardar y vincular contrato, supervisor, CDP y RP."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    contract_saved_confirmed: bool = False
    supervisor_section_found: bool = False
    supervisor_dialog_opened: bool = False
    supervisor_nature_selected: bool = False
    supervisor_id_type_selected: bool = False
    supervisor_document_written: bool = False
    supervisor_result_found: bool = False
    supervisor_selected: bool = False
    supervisor_type_internal_confirmed: bool = False
    supervisor_validate_clicked: bool = False
    supervisor_validation_confirmed: bool = False
    supervisor_link_clicked: bool = False
    supervisor_success_dialog_found: bool = False
    supervisor_success_dialog_accepted: bool = False
    supervisor_linked_confirmed: bool = False
    availability_section_found: bool = False
    availability_search_written: bool = False
    availability_result_found: bool = False
    availability_result_matches: bool = False
    availability_link_clicked: bool = False
    availability_link_success_found: bool = False
    availability_linked_row_confirmed: bool = False
    continue_button_found: bool = False
    continue_clicked: bool = False
    budget_register_section_found: bool = False
    budget_register_number_written: bool = False
    budget_register_date_provided: bool = False
    budget_register_date_written: bool = False
    budget_register_availability_selected: bool = False
    gross_total_written: bool = False
    budget_register_validate_clicked: bool = False
    budget_register_validation_confirmed: bool = False
    budget_register_link_clicked: bool = False
    budget_register_success_dialog_found: bool = False
    budget_register_success_dialog_accepted: bool = False
    budget_register_linked_confirmed: bool = False
    additional_dates_section_found: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "contract_saved_confirmed",
            "supervisor_section_found",
            "supervisor_dialog_opened",
            "supervisor_nature_selected",
            "supervisor_id_type_selected",
            "supervisor_document_written",
            "supervisor_result_found",
            "supervisor_selected",
            "supervisor_type_internal_confirmed",
            "supervisor_validate_clicked",
            "supervisor_validation_confirmed",
            "supervisor_link_clicked",
            "supervisor_success_dialog_found",
            "supervisor_success_dialog_accepted",
            "supervisor_linked_confirmed",
            "availability_section_found",
            "availability_search_written",
            "availability_result_found",
            "availability_result_matches",
            "availability_link_clicked",
            "availability_link_success_found",
            "availability_linked_row_confirmed",
            "continue_button_found",
            "continue_clicked",
            "budget_register_section_found",
            "budget_register_number_written",
            "budget_register_date_provided",
            "budget_register_date_written",
            "budget_register_availability_selected",
            "gross_total_written",
            "budget_register_validate_clicked",
            "budget_register_validation_confirmed",
            "budget_register_link_clicked",
            "budget_register_success_dialog_found",
            "budget_register_success_dialog_accepted",
            "budget_register_linked_confirmed",
            "additional_dates_section_found",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class BatchContractAdditionalDatesLinkProbeResult:
    """Resultado de guardar y vincular contrato hasta fechas adicionales."""

    success: bool
    code: str
    message: str
    authenticated: bool = False
    assistant_opened: bool = False
    contract_saved_confirmed: bool = False
    supervisor_linked_confirmed: bool = False
    availability_linked_row_confirmed: bool = False
    budget_register_linked_confirmed: bool = False
    additional_dates_section_found: bool = False
    additional_dates_any_provided: bool = False
    guarantee_approval_date_provided: bool = False
    guarantee_approval_date_written: bool = False
    website_publication_date_provided: bool = False
    website_publication_date_written: bool = False
    secop_publication_date_provided: bool = False
    secop_publication_date_written: bool = False
    additional_dates_validate_clicked: bool = False
    additional_dates_validation_confirmed: bool = False
    additional_dates_link_clicked: bool = False
    additional_dates_success_dialog_found: bool = False
    additional_dates_success_dialog_accepted: bool = False
    additional_dates_skipped: bool = False
    additional_dates_linked_confirmed: bool = False
    file_reported_section_found: bool = False
    duration_ms: int = 0

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        message = str(self.message).strip()
        if not code:
            raise ValueError("El código de la comprobación es obligatorio.")
        if not message:
            raise ValueError("El mensaje de la comprobación es obligatorio.")
        if self.duration_ms < 0:
            raise ValueError("La duración no puede ser negativa.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        for field_name in (
            "success",
            "authenticated",
            "assistant_opened",
            "contract_saved_confirmed",
            "supervisor_linked_confirmed",
            "availability_linked_row_confirmed",
            "budget_register_linked_confirmed",
            "additional_dates_section_found",
            "additional_dates_any_provided",
            "guarantee_approval_date_provided",
            "guarantee_approval_date_written",
            "website_publication_date_provided",
            "website_publication_date_written",
            "secop_publication_date_provided",
            "secop_publication_date_written",
            "additional_dates_validate_clicked",
            "additional_dates_validation_confirmed",
            "additional_dates_link_clicked",
            "additional_dates_success_dialog_found",
            "additional_dates_success_dialog_accepted",
            "additional_dates_skipped",
            "additional_dates_linked_confirmed",
            "file_reported_section_found",
        ):
            object.__setattr__(
                self,
                field_name,
                bool(getattr(self, field_name)),
            )


class BatchPortalProbe(Protocol):
    """Expone diagnósticos y guardado controlado del formulario contractual."""

    @property
    def name(self) -> str:
        ...

    def probe(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ) -> BatchPortalProbeResult:
        ...

    def probe_assistant_form(
        self,
        *,
        portal_username: str,
        portal_password: str,
    ) -> BatchAssistantProbeResult:
        ...

    def probe_header_draft(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchHeaderDraftProbeResult:
        ...


    def probe_header_validation(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchHeaderValidationProbeResult:
        ...

    def probe_general_data_draft(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchGeneralDataDraftProbeResult:
        ...

    def probe_general_completion_draft(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchGeneralCompletionDraftProbeResult:
        ...

    def probe_general_validation(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchGeneralValidationProbeResult:
        ...

    def probe_contract_save(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractSaveProbeResult:
        ...

    def probe_contract_supervisor_link(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractSupervisorLinkProbeResult:
        ...

    def probe_contract_availability_link(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractAvailabilityLinkProbeResult:
        ...

    def probe_contract_budget_register_link(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractBudgetRegisterLinkProbeResult:
        ...

    def probe_contract_additional_dates_link(
        self,
        *,
        portal_username: str,
        portal_password: str,
        contract: ContractData,
    ) -> BatchContractAdditionalDatesLinkProbeResult:
        ...


