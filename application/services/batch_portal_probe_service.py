from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

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
from application.ports.batch_portal_probe import BatchPortalProbe
from application.ports.batch_repository import BatchRepository
from application.ports.credential_cipher import CredentialCipher
from application.ports.portal_credential_repository import (
    PortalCredentialRepository,
)
from domain.enums.batch_status import BatchStatus
from domain.errors.batch_errors import BatchNotFoundError
from domain.errors.batch_portal_probe_errors import (
    BatchPortalProbeBlockedError,
    BatchPortalProbeConfigurationError,
)
from domain.models.contract_batch import ContractBatch
from domain.models.portal_credentials import PortalCredentials


class BatchPortalProbeService:
    """Ejecuta diagnósticos y operaciones controladas contra el portal."""

    def __init__(
        self,
        *,
        batches: BatchRepository,
        credentials: PortalCredentialRepository,
        cipher: CredentialCipher | None,
        probe: BatchPortalProbe,
        credential_max_age_hours: int = 24,
    ) -> None:
        if credential_max_age_hours <= 0:
            raise ValueError(
                "La vigencia de la prueba de credenciales debe ser positiva."
            )
        self._batches = batches
        self._credentials = credentials
        self._cipher = cipher
        self._probe = probe
        self._credential_max_age = timedelta(
            hours=credential_max_age_hours
        )

    def run(
        self,
        *,
        batch_id: UUID,
        dependency: str,
        allow_processing: bool = False,
    ) -> BatchPortalProbeOutcome:
        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
            allow_processing=allow_processing,
        )

        try:
            result = self._probe.probe(
                portal_username=credential.portal_username,
                portal_password=portal_password,
            )
        finally:
            portal_password = ""

        return BatchPortalProbeOutcome(
            batch_id=batch.batch_id,
            dependency=batch.dependency,
            probe_name=self._probe.name,
            success=result.success,
            code=result.code,
            message=result.message,
            authenticated=result.authenticated,
            contracting_menu_found=result.contracting_menu_found,
            enter_contract_found=result.enter_contract_found,
            assistant_access_found=result.assistant_access_found,
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )

    def run_assistant_form(
        self,
        *,
        batch_id: UUID,
        dependency: str,
    ) -> BatchAssistantProbeOutcome:
        """Abre el asistente y comprueba C1-C2 sin completar campos."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )

        try:
            result = self._probe.probe_assistant_form(
                portal_username=credential.portal_username,
                portal_password=portal_password,
            )
        finally:
            portal_password = ""

        return BatchAssistantProbeOutcome(
            batch_id=batch.batch_id,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-assistant-form",
            success=result.success,
            code=result.code,
            message=result.message,
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            assistant_container_found=result.assistant_container_found,
            record_type_found=result.record_type_found,
            contract_number_found=result.contract_number_found,
            contractor_search_found=result.contractor_search_found,
            project_search_found=result.project_search_found,
            validate_button_found=result.validate_button_found,
            missing_controls=result.missing_controls,
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )

    def run_header_draft(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> BatchHeaderDraftProbeOutcome:
        """Completa un único encabezado C1-C2 sin pulsar Validar."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )

        item = next(
            (candidate for candidate in batch.contracts if candidate.item_id == item_id),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        try:
            result = self._probe.probe_header_draft(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=item.contract,
            )
        finally:
            portal_password = ""

        return BatchHeaderDraftProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-header-draft",
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=item.contract.contract_number,
            contractor_document=item.contract.contractor.document_number,
            contractor_nature=item.contract.contractor.nature.value,
            project_code=item.contract.project_code,
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            record_type_selected=result.record_type_selected,
            contract_number_written=result.contract_number_written,
            contractor_dialog_opened=result.contractor_dialog_opened,
            contractor_nature_selected=result.contractor_nature_selected,
            contractor_document_written=result.contractor_document_written,
            contractor_result_found=result.contractor_result_found,
            contractor_selected=result.contractor_selected,
            project_dialog_opened=result.project_dialog_opened,
            project_code_written=result.project_code_written,
            project_result_found=result.project_result_found,
            project_selected=result.project_selected,
            validate_button_found=result.validate_button_found,
            validate_clicked=result.validate_clicked,
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )


    def run_header_validation(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> BatchHeaderValidationProbeOutcome:
        """Valida C1-C2 y comprueba C3 sin completar ni guardar."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )

        item = next(
            (
                candidate
                for candidate in batch.contracts
                if candidate.item_id == item_id
            ),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        try:
            result = self._probe.probe_header_validation(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=item.contract,
            )
        finally:
            portal_password = ""

        return BatchHeaderValidationProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-header-validation",
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=item.contract.contract_number,
            contractor_document=item.contract.contractor.document_number,
            contractor_nature=item.contract.contractor.nature.value,
            project_code=item.contract.project_code,
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            record_type_selected=result.record_type_selected,
            contract_number_written=result.contract_number_written,
            contractor_selected=result.contractor_selected,
            project_selected=result.project_selected,
            validate_button_found=result.validate_button_found,
            validate_clicked=result.validate_clicked,
            header_validation_confirmed=(
                result.header_validation_confirmed
            ),
            general_data_ready=result.general_data_ready,
            general_object_found=result.general_object_found,
            general_signing_date_found=(
                result.general_signing_date_found
            ),
            general_starting_date_found=(
                result.general_starting_date_found
            ),
            general_amount_found=result.general_amount_found,
            general_contract_term_found=(
                result.general_contract_term_found
            ),
            missing_controls=result.missing_controls,
            save_clicked=result.save_clicked,
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )

    def run_general_data_draft(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> BatchGeneralDataDraftProbeOutcome:
        """Completa C3 para un contrato sin validar ni guardar."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )

        item = next(
            (
                candidate
                for candidate in batch.contracts
                if candidate.item_id == item_id
            ),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        try:
            result = self._probe.probe_general_data_draft(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=item.contract,
            )
        finally:
            portal_password = ""

        contract = item.contract
        return BatchGeneralDataDraftProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-general-data-draft",
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=contract.contract_number,
            contractor_document=contract.contractor.document_number,
            contractor_nature=contract.contractor.nature.value,
            project_code=contract.project_code,
            object_description=contract.object_description,
            signing_date=contract.signing_date.isoformat(),
            starting_date=contract.starting_date.isoformat(),
            amount=format(contract.amount, "f"),
            term_days=contract.term_days,
            process_type=contract.process_type,
            procedure=contract.procedure,
            contract_type=contract.contract_type,
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            header_validation_confirmed=(
                result.header_validation_confirmed
            ),
            object_written=result.object_written,
            signing_date_written=result.signing_date_written,
            starting_date_written=result.starting_date_written,
            amount_written=result.amount_written,
            amount_in_words_generated=(
                result.amount_in_words_generated
            ),
            contract_term_written=result.contract_term_written,
            term_unit_days_selected=result.term_unit_days_selected,
            process_type_selected=result.process_type_selected,
            procedure_selected=result.procedure_selected,
            contract_type_selected=result.contract_type_selected,
            other_currency_no_selected=(
                result.other_currency_no_selected
            ),
            general_data_completed=result.general_data_completed,
            general_validate_clicked=result.general_validate_clicked,
            save_clicked=result.save_clicked,
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )


    def run_general_completion_draft(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> BatchGeneralCompletionDraftProbeOutcome:
        """Completa C3-C4 para un contrato sin validar ni guardar."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )

        item = next(
            (
                candidate
                for candidate in batch.contracts
                if candidate.item_id == item_id
            ),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        try:
            result = self._probe.probe_general_completion_draft(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=item.contract,
            )
        finally:
            portal_password = ""

        contract = item.contract
        return BatchGeneralCompletionDraftProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-general-completion-draft",
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=contract.contract_number,
            contractor_document=contract.contractor.document_number,
            contractor_nature=contract.contractor.nature.value,
            project_code=contract.project_code,
            budget_year=contract.budget.year,
            budget_item=contract.budget.item,
            budget_subsector=contract.budget.subsector,
            secop_url=str(contract.secop_url or ""),
            execution_department="Antioquia",
            execution_city="Medellín",
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            header_validation_confirmed=(
                result.header_validation_confirmed
            ),
            general_data_completed=result.general_data_completed,
            government_plan_selected=(
                result.government_plan_selected
            ),
            budget_year_selected=result.budget_year_selected,
            budget_item_selected=result.budget_item_selected,
            budget_subsector_selected=(
                result.budget_subsector_selected
            ),
            budget_link_clicked=result.budget_link_clicked,
            secop_yes_selected=result.secop_yes_selected,
            secop_url_written=result.secop_url_written,
            advance_no_selected=result.advance_no_selected,
            commercial_trust_no_selected=(
                result.commercial_trust_no_selected
            ),
            urgency_no_selected=result.urgency_no_selected,
            future_commitment_no_selected=(
                result.future_commitment_no_selected
            ),
            cooperation_contract_no_selected=(
                result.cooperation_contract_no_selected
            ),
            execution_department_selected=(
                result.execution_department_selected
            ),
            execution_city_selected=result.execution_city_selected,
            final_validate_button_found=(
                result.final_validate_button_found
            ),
            general_completion_completed=(
                result.general_completion_completed
            ),
            general_validate_clicked=result.general_validate_clicked,
            save_clicked=result.save_clicked,
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )


    def run_general_validation(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
    ) -> BatchGeneralValidationProbeOutcome:
        """Valida C3-C4 y confirma Guardar sin pulsarlo."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )

        item = next(
            (
                candidate
                for candidate in batch.contracts
                if candidate.item_id == item_id
            ),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        try:
            result = self._probe.probe_general_validation(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=item.contract,
            )
        finally:
            portal_password = ""

        contract = item.contract
        return BatchGeneralValidationProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-general-validation",
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=contract.contract_number,
            contractor_document=contract.contractor.document_number,
            contractor_nature=contract.contractor.nature.value,
            project_code=contract.project_code,
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            header_validation_confirmed=(
                result.header_validation_confirmed
            ),
            general_data_completed=result.general_data_completed,
            general_completion_completed=(
                result.general_completion_completed
            ),
            final_validate_button_found=(
                result.final_validate_button_found
            ),
            general_validate_clicked=result.general_validate_clicked,
            general_validation_confirmed=(
                result.general_validation_confirmed
            ),
            save_button_found=result.save_button_found,
            save_clicked=result.save_clicked,
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )


    def run_contract_save(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        allow_test_values: bool,
    ) -> BatchContractSaveProbeOutcome:
        """Guarda un contrato autorizado y confirma la etapa de supervisor."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )

        item = next(
            (
                candidate
                for candidate in batch.contracts
                if candidate.item_id == item_id
            ),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        expected_confirmation = (
            f"GUARDAR {item.contract.contract_number}"
        )
        received_confirmation = " ".join(
            str(confirmation).strip().split()
        )
        if received_confirmation.casefold() != expected_confirmation.casefold():
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La confirmación no coincide. Escriba exactamente: "
                f"{expected_confirmation}"
            )

        if (
            item.contract.amount <= Decimal("1")
            and not bool(allow_test_values)
        ):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato usa un valor de prueba. Debe autorizar "
                "explícitamente allow_test_values=true."
            )

        try:
            result = self._probe.probe_contract_save(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=item.contract,
            )
        finally:
            portal_password = ""

        contract = item.contract
        return BatchContractSaveProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-contract-save",
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=contract.contract_number,
            contractor_document=contract.contractor.document_number,
            contractor_nature=contract.contractor.nature.value,
            project_code=contract.project_code,
            amount=format(contract.amount, "f"),
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            header_validation_confirmed=(
                result.header_validation_confirmed
            ),
            general_data_completed=result.general_data_completed,
            general_completion_completed=(
                result.general_completion_completed
            ),
            general_validation_confirmed=(
                result.general_validation_confirmed
            ),
            save_button_found=result.save_button_found,
            save_clicked=result.save_clicked,
            success_dialog_found=result.success_dialog_found,
            success_dialog_accepted=result.success_dialog_accepted,
            contract_saved_confirmed=(
                result.contract_saved_confirmed
            ),
            supervisor_section_found=(
                result.supervisor_section_found
            ),
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )


    def run_contract_supervisor_link(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        allow_test_values: bool,
    ) -> BatchContractSupervisorLinkProbeOutcome:
        """Guarda un contrato y vincula su supervisor interno."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )

        item = next(
            (
                candidate
                for candidate in batch.contracts
                if candidate.item_id == item_id
            ),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        expected_confirmation = (
            f"GUARDAR Y VINCULAR {item.contract.contract_number}"
        )
        received_confirmation = " ".join(
            str(confirmation).strip().split()
        )
        if received_confirmation.casefold() != expected_confirmation.casefold():
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La confirmación no coincide. Escriba exactamente: "
                f"{expected_confirmation}"
            )

        if (
            item.contract.amount <= Decimal("1")
            and not bool(allow_test_values)
        ):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato usa un valor de prueba. Debe autorizar "
                "explícitamente allow_test_values=true."
            )

        supervisor_document = str(
            item.contract.supervisor.document_number
        ).strip()
        if not supervisor_document:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La cédula del supervisor es obligatoria."
            )

        supervisor_type = str(
            item.contract.supervisor.supervisor_type or "Interno"
        ).strip()
        if supervisor_type.casefold() != "interno":
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La regla administrativa exige supervisor de tipo Interno."
            )

        try:
            result = self._probe.probe_contract_supervisor_link(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=item.contract,
            )
        finally:
            portal_password = ""

        contract = item.contract
        return BatchContractSupervisorLinkProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-contract-supervisor-link",
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=contract.contract_number,
            supervisor_document=supervisor_document,
            supervisor_type="Interno",
            amount=format(contract.amount, "f"),
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            contract_saved_confirmed=result.contract_saved_confirmed,
            supervisor_section_found=result.supervisor_section_found,
            supervisor_dialog_opened=result.supervisor_dialog_opened,
            supervisor_nature_selected=result.supervisor_nature_selected,
            supervisor_id_type_selected=(
                result.supervisor_id_type_selected
            ),
            supervisor_document_written=(
                result.supervisor_document_written
            ),
            supervisor_result_found=result.supervisor_result_found,
            supervisor_selected=result.supervisor_selected,
            supervisor_type_internal_confirmed=(
                result.supervisor_type_internal_confirmed
            ),
            supervisor_validate_clicked=(
                result.supervisor_validate_clicked
            ),
            supervisor_validation_confirmed=(
                result.supervisor_validation_confirmed
            ),
            supervisor_link_clicked=result.supervisor_link_clicked,
            success_dialog_found=result.success_dialog_found,
            success_dialog_accepted=result.success_dialog_accepted,
            supervisor_linked_confirmed=(
                result.supervisor_linked_confirmed
            ),
            availability_section_found=(
                result.availability_section_found
            ),
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )


    def run_contract_availability_link(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        allow_test_values: bool,
    ) -> BatchContractAvailabilityLinkProbeOutcome:
        """Guarda contrato, vincula supervisor y disponibilidad CDP."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )
        item = next(
            (candidate for candidate in batch.contracts if candidate.item_id == item_id),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        expected_confirmation = (
            f"GUARDAR SUPERVISOR Y CDP {item.contract.contract_number}"
        )
        received_confirmation = " ".join(
            str(confirmation).strip().split()
        )
        if received_confirmation.casefold() != expected_confirmation.casefold():
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La confirmación no coincide. Escriba exactamente: "
                f"{expected_confirmation}"
            )

        if item.contract.amount <= Decimal("1") and not bool(allow_test_values):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato usa un valor de prueba. Debe autorizar "
                "explícitamente allow_test_values=true."
            )

        supervisor_document = str(
            item.contract.supervisor.document_number
        ).strip()
        if not supervisor_document:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La cédula del supervisor es obligatoria."
            )
        supervisor_type = str(
            item.contract.supervisor.supervisor_type or "Interno"
        ).strip()
        if supervisor_type.casefold() != "interno":
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La regla administrativa exige supervisor de tipo Interno."
            )
        cdp_code = str(item.contract.budget.cdp_code).strip()
        if not cdp_code:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El número de CDP es obligatorio."
            )

        try:
            result = self._probe.probe_contract_availability_link(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=item.contract,
            )
        finally:
            portal_password = ""

        contract = item.contract
        return BatchContractAvailabilityLinkProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=f"{self._probe.name}-contract-availability-link",
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=contract.contract_number,
            supervisor_document=supervisor_document,
            supervisor_type="Interno",
            cdp_code=cdp_code,
            amount=format(contract.amount, "f"),
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            contract_saved_confirmed=result.contract_saved_confirmed,
            supervisor_section_found=result.supervisor_section_found,
            supervisor_dialog_opened=result.supervisor_dialog_opened,
            supervisor_nature_selected=result.supervisor_nature_selected,
            supervisor_id_type_selected=result.supervisor_id_type_selected,
            supervisor_document_written=result.supervisor_document_written,
            supervisor_result_found=result.supervisor_result_found,
            supervisor_selected=result.supervisor_selected,
            supervisor_type_internal_confirmed=result.supervisor_type_internal_confirmed,
            supervisor_validate_clicked=result.supervisor_validate_clicked,
            supervisor_validation_confirmed=result.supervisor_validation_confirmed,
            supervisor_link_clicked=result.supervisor_link_clicked,
            supervisor_success_dialog_found=result.supervisor_success_dialog_found,
            supervisor_success_dialog_accepted=result.supervisor_success_dialog_accepted,
            supervisor_linked_confirmed=result.supervisor_linked_confirmed,
            availability_section_found=result.availability_section_found,
            availability_search_written=result.availability_search_written,
            availability_result_found=result.availability_result_found,
            availability_result_matches=result.availability_result_matches,
            availability_link_clicked=result.availability_link_clicked,
            availability_link_success_found=result.availability_link_success_found,
            availability_linked_row_confirmed=result.availability_linked_row_confirmed,
            continue_button_found=result.continue_button_found,
            continue_clicked=result.continue_clicked,
            budget_register_section_found=result.budget_register_section_found,
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )


    def run_contract_budget_register_link(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        allow_test_values: bool,
    ) -> BatchContractBudgetRegisterLinkProbeOutcome:
        """Guarda y vincula supervisor, CDP y registro presupuestal."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )
        item = next(
            (
                candidate
                for candidate in batch.contracts
                if candidate.item_id == item_id
            ),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        expected_confirmation = (
            "GUARDAR SUPERVISOR CDP Y RP "
            f"{item.contract.contract_number}"
        )
        received_confirmation = " ".join(
            str(confirmation).strip().split()
        )
        if (
            received_confirmation.casefold()
            != expected_confirmation.casefold()
        ):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La confirmación no coincide. Escriba exactamente: "
                f"{expected_confirmation}"
            )

        contract = item.contract
        if (
            contract.amount <= Decimal("1")
            or contract.budget.gross_total <= Decimal("1")
        ) and not bool(allow_test_values):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato usa valores de prueba. Debe autorizar "
                "explícitamente allow_test_values=true."
            )

        supervisor_document = str(
            contract.supervisor.document_number
        ).strip()
        if not supervisor_document:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La cédula del supervisor es obligatoria."
            )
        supervisor_type = str(
            contract.supervisor.supervisor_type or "Interno"
        ).strip()
        if supervisor_type.casefold() != "interno":
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La regla administrativa exige supervisor de tipo Interno."
            )
        cdp_code = str(contract.budget.cdp_code).strip()
        if not cdp_code:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El número de CDP es obligatorio."
            )
        register_number = str(
            contract.budget.budget_register_number or ""
        ).strip()
        if not register_number:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El número de registro presupuestal es obligatorio."
            )
        if contract.budget.gross_total <= Decimal("0"):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El Total Bruto debe ser mayor que cero."
            )

        try:
            result = self._probe.probe_contract_budget_register_link(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=contract,
            )
        finally:
            portal_password = ""

        register_date = contract.budget.budget_register_date
        return BatchContractBudgetRegisterLinkProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=(
                f"{self._probe.name}-contract-budget-register-link"
            ),
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=contract.contract_number,
            supervisor_document=supervisor_document,
            cdp_code=cdp_code,
            budget_register_number=register_number,
            budget_register_date=(
                register_date.isoformat()
                if register_date is not None
                else None
            ),
            gross_total=format(contract.budget.gross_total, "f"),
            amount=format(contract.amount, "f"),
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            contract_saved_confirmed=result.contract_saved_confirmed,
            supervisor_linked_confirmed=result.supervisor_linked_confirmed,
            availability_linked_row_confirmed=(
                result.availability_linked_row_confirmed
            ),
            budget_register_section_found=(
                result.budget_register_section_found
            ),
            budget_register_number_written=(
                result.budget_register_number_written
            ),
            budget_register_date_provided=(
                result.budget_register_date_provided
            ),
            budget_register_date_written=(
                result.budget_register_date_written
            ),
            budget_register_availability_selected=(
                result.budget_register_availability_selected
            ),
            gross_total_written=result.gross_total_written,
            budget_register_validate_clicked=(
                result.budget_register_validate_clicked
            ),
            budget_register_validation_confirmed=(
                result.budget_register_validation_confirmed
            ),
            budget_register_link_clicked=(
                result.budget_register_link_clicked
            ),
            budget_register_success_dialog_found=(
                result.budget_register_success_dialog_found
            ),
            budget_register_success_dialog_accepted=(
                result.budget_register_success_dialog_accepted
            ),
            budget_register_linked_confirmed=(
                result.budget_register_linked_confirmed
            ),
            additional_dates_section_found=(
                result.additional_dates_section_found
            ),
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )



    def run_contract_additional_dates_link(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        dependency: str,
        confirmation: str,
        allow_test_values: bool,
    ) -> BatchContractAdditionalDatesLinkProbeOutcome:
        """Guarda el contrato y vincula supervisor, CDP, RP y C9."""

        batch, credential, portal_password = self._prepare_probe(
            batch_id=batch_id,
            dependency=dependency,
        )
        item = next(
            (
                candidate
                for candidate in batch.contracts
                if candidate.item_id == item_id
            ),
            None,
        )
        if item is None:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato seleccionado no pertenece al lote indicado."
            )

        expected_confirmation = (
            "GUARDAR SUPERVISOR CDP RP Y FECHAS "
            f"{item.contract.contract_number}"
        )
        received_confirmation = " ".join(
            str(confirmation).strip().split()
        )
        if (
            received_confirmation.casefold()
            != expected_confirmation.casefold()
        ):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La confirmación no coincide. Escriba exactamente: "
                f"{expected_confirmation}"
            )

        contract = item.contract
        if (
            contract.amount <= Decimal("1")
            or contract.budget.gross_total <= Decimal("1")
        ) and not bool(allow_test_values):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El contrato usa valores de prueba. Debe autorizar "
                "explícitamente allow_test_values=true."
            )

        supervisor_document = str(
            contract.supervisor.document_number
        ).strip()
        if not supervisor_document:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La cédula del supervisor es obligatoria."
            )
        supervisor_type = str(
            contract.supervisor.supervisor_type or "Interno"
        ).strip()
        if supervisor_type.casefold() != "interno":
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "La regla administrativa exige supervisor de tipo Interno."
            )
        cdp_code = str(contract.budget.cdp_code).strip()
        if not cdp_code:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El número de CDP es obligatorio."
            )
        register_number = str(
            contract.budget.budget_register_number or ""
        ).strip()
        if not register_number:
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El número de registro presupuestal es obligatorio."
            )
        if contract.budget.gross_total <= Decimal("0"):
            portal_password = ""
            raise BatchPortalProbeBlockedError(
                "El Total Bruto debe ser mayor que cero."
            )

        try:
            result = self._probe.probe_contract_additional_dates_link(
                portal_username=credential.portal_username,
                portal_password=portal_password,
                contract=contract,
            )
        finally:
            portal_password = ""

        return BatchContractAdditionalDatesLinkProbeOutcome(
            batch_id=batch.batch_id,
            item_id=item.item_id,
            row_number=item.source_row_number,
            dependency=batch.dependency,
            probe_name=(
                f"{self._probe.name}-contract-additional-dates-link"
            ),
            success=result.success,
            code=result.code,
            message=result.message,
            contract_number=contract.contract_number,
            cdp_code=cdp_code,
            budget_register_number=register_number,
            guarantee_approval_date=(
                contract.guarantee_approval_date.isoformat()
                if contract.guarantee_approval_date is not None
                else None
            ),
            website_publication_date=(
                contract.website_publication_date.isoformat()
                if contract.website_publication_date is not None
                else None
            ),
            secop_publication_date=(
                contract.secop_publication_date.isoformat()
                if contract.secop_publication_date is not None
                else None
            ),
            amount=format(contract.amount, "f"),
            authenticated=result.authenticated,
            assistant_opened=result.assistant_opened,
            contract_saved_confirmed=result.contract_saved_confirmed,
            supervisor_linked_confirmed=(
                result.supervisor_linked_confirmed
            ),
            availability_linked_row_confirmed=(
                result.availability_linked_row_confirmed
            ),
            budget_register_linked_confirmed=(
                result.budget_register_linked_confirmed
            ),
            additional_dates_section_found=(
                result.additional_dates_section_found
            ),
            additional_dates_any_provided=(
                result.additional_dates_any_provided
            ),
            guarantee_approval_date_provided=(
                result.guarantee_approval_date_provided
            ),
            guarantee_approval_date_written=(
                result.guarantee_approval_date_written
            ),
            website_publication_date_provided=(
                result.website_publication_date_provided
            ),
            website_publication_date_written=(
                result.website_publication_date_written
            ),
            secop_publication_date_provided=(
                result.secop_publication_date_provided
            ),
            secop_publication_date_written=(
                result.secop_publication_date_written
            ),
            additional_dates_validate_clicked=(
                result.additional_dates_validate_clicked
            ),
            additional_dates_validation_confirmed=(
                result.additional_dates_validation_confirmed
            ),
            additional_dates_link_clicked=(
                result.additional_dates_link_clicked
            ),
            additional_dates_success_dialog_found=(
                result.additional_dates_success_dialog_found
            ),
            additional_dates_success_dialog_accepted=(
                result.additional_dates_success_dialog_accepted
            ),
            additional_dates_skipped=result.additional_dates_skipped,
            additional_dates_linked_confirmed=(
                result.additional_dates_linked_confirmed
            ),
            file_reported_section_found=(
                result.file_reported_section_found
            ),
            duration_ms=result.duration_ms,
            checked_at=datetime.now(UTC),
        )


    def _prepare_probe(
        self,
        *,
        batch_id: UUID,
        dependency: str,
        allow_processing: bool = False,
    ) -> tuple[ContractBatch, PortalCredentials, str]:
        batch = self._batches.get_by_id(
            batch_id,
            dependency=dependency,
        )
        if batch is None:
            raise BatchNotFoundError(str(batch_id))
        allowed_statuses = {BatchStatus.READY}
        if allow_processing:
            allowed_statuses.add(BatchStatus.PROCESSING)

        if batch.status not in allowed_statuses:
            expected = (
                "READY o PROCESSING"
                if allow_processing
                else "READY"
            )
            raise BatchPortalProbeBlockedError(
                "La comprobación del portal solo está disponible para "
                f"lotes {expected}. Estado actual: {batch.status.value}."
            )

        credential = self._credentials.find_by_dependency(dependency)
        if credential is None:
            raise BatchPortalProbeBlockedError(
                "No hay credenciales de Gestión Transparente configuradas "
                "para la dependencia."
            )
        if credential.last_test_success is not True:
            raise BatchPortalProbeBlockedError(
                "Las credenciales deben tener una prueba exitosa antes de "
                "comprobar el portal."
            )
        if credential.last_tested_at is None:
            raise BatchPortalProbeBlockedError(
                "No existe fecha de la última prueba de credenciales."
            )

        tested_at = credential.last_tested_at
        if tested_at.tzinfo is None:
            tested_at = tested_at.replace(tzinfo=UTC)
        age = datetime.now(UTC) - tested_at.astimezone(UTC)
        if age > self._credential_max_age:
            raise BatchPortalProbeBlockedError(
                "La última prueba de credenciales expiró. Vuelva a probarlas "
                "desde Configuración."
            )

        if self._cipher is None:
            raise BatchPortalProbeConfigurationError(
                "El cifrado Fernet no está configurado."
            )

        try:
            portal_password = self._cipher.decrypt(
                credential.encrypted_password
            )
        except Exception as error:
            raise BatchPortalProbeConfigurationError(
                "No fue posible descifrar las credenciales del portal."
            ) from error

        return batch, credential, portal_password
