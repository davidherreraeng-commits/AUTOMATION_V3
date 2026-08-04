from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from application.ports.execution_repository import ExecutionRepositoryError
from application.services.batch_creation_service import BatchCreationService
from application.services.batch_contract_execution_service import (
    BatchContractExecutionService,
)
from application.services.batch_execution_service import BatchExecutionService
from application.services.batch_portal_probe_service import (
    BatchPortalProbeService,
)
from domain.errors.batch_contract_execution_errors import (
    BatchContractExecutionBlockedError,
    BatchContractExecutionConfirmationError,
    BatchContractExecutionIdentityError,
    BatchContractExecutionInProgressError,
    BatchContractExecutionStateError,
    BatchContractItemNotFoundError,
)
from domain.errors.batch_execution_errors import (
    BatchExecutionBlockedError,
    BatchExecutionInProgressError,
    BatchExecutionStateError,
    BatchNotReadyForExecutionError,
)
from domain.errors.batch_portal_probe_errors import (
    BatchPortalProbeBlockedError,
    BatchPortalProbeConfigurationError,
)
from domain.errors.batch_errors import (
    BatchAlreadyExistsError,
    BatchNotFoundError,
    BatchRepositoryError,
    InvalidBatchSelectionError,
    StoredValidationCorruptedError,
    StoredValidationNotFoundError,
)
from interfaces.api.dependencies import (
    CurrentUser,
    Superuser,
    get_batch_creation_service,
    get_batch_contract_execution_service,
    get_batch_execution_service,
    get_batch_portal_probe_service,
)
from interfaces.api.schemas.batches import (
    BatchContractExecutionPreflightResponse,
    BatchContractExecutionRequest,
    BatchContractExecutionResponse,
    BatchAssistantProbeResponse,
    BatchContractSaveProbeRequest,
    BatchContractSaveProbeResponse,
    BatchContractSupervisorLinkProbeRequest,
    BatchContractAvailabilityLinkProbeRequest,
    BatchContractBudgetRegisterLinkProbeRequest,
    BatchContractAdditionalDatesLinkProbeRequest,
    BatchContractSupervisorLinkProbeResponse,
    BatchContractAvailabilityLinkProbeResponse,
    BatchContractBudgetRegisterLinkProbeResponse,
    BatchContractAdditionalDatesLinkProbeResponse,
    BatchGeneralCompletionDraftProbeRequest,
    BatchGeneralCompletionDraftProbeResponse,
    BatchGeneralDataDraftProbeRequest,
    BatchGeneralDataDraftProbeResponse,
    BatchGeneralValidationProbeRequest,
    BatchGeneralValidationProbeResponse,
    BatchHeaderDraftProbeRequest,
    BatchHeaderDraftProbeResponse,
    BatchHeaderValidationProbeRequest,
    BatchHeaderValidationProbeResponse,
    BatchCreateRequest,
    BatchExecutionPreflightResponse,
    BatchExecutionStatusResponse,
    BatchListResponse,
    BatchPortalProbeResponse,
    BatchResponse,
)


router = APIRouter(prefix="/batches", tags=["Lotes de contratos"])


@router.post(
    "",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_batch(
    payload: BatchCreateRequest,
    actor: CurrentUser,
    service: Annotated[
        BatchCreationService,
        Depends(get_batch_creation_service),
    ],
) -> BatchResponse:
    try:
        batch = service.create(
            validation_id=payload.validation_id,
            selected_row_numbers=payload.selected_row_numbers,
            actor_user_id=actor.user_id,
            actor_username=actor.username,
            dependency=actor.dependency,
        )
    except StoredValidationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except InvalidBatchSelectionError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except BatchAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except StoredValidationCorruptedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible persistir el lote en este momento.",
        ) from error

    return BatchResponse.from_domain(batch)


@router.get("", response_model=BatchListResponse)
def list_batches(
    actor: CurrentUser,
    service: Annotated[
        BatchCreationService,
        Depends(get_batch_creation_service),
    ],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> BatchListResponse:
    try:
        batches = service.list(
            dependency=actor.dependency,
            limit=limit,
        )
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar los lotes en este momento.",
        ) from error
    return BatchListResponse.from_domain(batches)


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(
    batch_id: UUID,
    actor: CurrentUser,
    service: Annotated[
        BatchCreationService,
        Depends(get_batch_creation_service),
    ],
) -> BatchResponse:
    try:
        batch = service.get(
            batch_id=batch_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar el lote en este momento.",
        ) from error
    return BatchResponse.from_domain(batch)


@router.get(
    "/{batch_id}/execution/preflight",
    response_model=BatchExecutionPreflightResponse,
)
def execution_preflight(
    batch_id: UUID,
    actor: Superuser,
    service: Annotated[
        BatchExecutionService,
        Depends(get_batch_execution_service),
    ],
) -> BatchExecutionPreflightResponse:
    try:
        preflight = service.preflight(
            batch_id=batch_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible comprobar el lote en este momento.",
        ) from error
    return BatchExecutionPreflightResponse.from_domain(preflight)



@router.get(
    "/{batch_id}/contracts/{item_id}/execution/preflight",
    response_model=BatchContractExecutionPreflightResponse,
)
def contract_execution_preflight(
    batch_id: UUID,
    item_id: UUID,
    actor: Superuser,
    service: Annotated[
        BatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
) -> BatchContractExecutionPreflightResponse:
    try:
        preflight = service.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchContractItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        BatchRepositoryError,
        ExecutionRepositoryError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible comprobar el contrato seleccionado."
            ),
        ) from error

    return BatchContractExecutionPreflightResponse.from_domain(preflight)


@router.post(
    "/{batch_id}/contracts/{item_id}/execution",
    response_model=BatchContractExecutionResponse,
)
def execute_selected_contract(
    batch_id: UUID,
    item_id: UUID,
    payload: BatchContractExecutionRequest,
    actor: Superuser,
    service: Annotated[
        BatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
) -> BatchContractExecutionResponse:
    try:
        result = service.execute(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            confirmation=payload.confirmation,
            execution_id=payload.execution_id,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchContractItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchContractExecutionConfirmationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WRITE_CONFIRMATION_REQUIRED",
                "message": str(error),
                "required_confirmation": error.required_confirmation,
            },
        ) from error
    except BatchContractExecutionBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONTRACT_EXECUTION_BLOCKED",
                "message": str(error),
                "issues": [
                    {"code": code, "message": message}
                    for code, message in error.issues
                ],
            },
        ) from error
    except (
        BatchContractExecutionIdentityError,
        BatchContractExecutionInProgressError,
        BatchContractExecutionStateError,
        BatchExecutionInProgressError,
        BatchNotReadyForExecutionError,
        BatchExecutionStateError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except (
        BatchRepositoryError,
        ExecutionRepositoryError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible ejecutar el contrato seleccionado."
            ),
        ) from error

    return BatchContractExecutionResponse.from_domain(result)


@router.get(
    "/{batch_id}/contracts/{item_id}/execution",
    response_model=BatchContractExecutionResponse,
)
def get_selected_contract_execution(
    batch_id: UUID,
    item_id: UUID,
    actor: Superuser,
    service: Annotated[
        BatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
) -> BatchContractExecutionResponse:
    try:
        result = service.status(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchContractItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        BatchRepositoryError,
        ExecutionRepositoryError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible consultar el checkpoint del contrato."
            ),
        ) from error

    return BatchContractExecutionResponse.from_domain(result)


@router.post(
    "/{batch_id}/execution/probe",
    response_model=BatchPortalProbeResponse,
)
def probe_batch_portal_navigation(
    batch_id: UUID,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchPortalProbeResponse:
    try:
        outcome = service.run(
            batch_id=batch_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible comprobar el acceso al portal.",
        ) from error

    return BatchPortalProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/assistant-probe",
    response_model=BatchAssistantProbeResponse,
)
def probe_batch_assistant_form(
    batch_id: UUID,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchAssistantProbeResponse:
    """Abre el asistente y comprueba C1-C2 sin escribir datos."""

    try:
        outcome = service.run_assistant_form(
            batch_id=batch_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible comprobar el formulario contractual.",
        ) from error

    return BatchAssistantProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/header-draft-probe",
    response_model=BatchHeaderDraftProbeResponse,
)
def probe_batch_header_draft(
    batch_id: UUID,
    payload: BatchHeaderDraftProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchHeaderDraftProbeResponse:
    """Completa un encabezado C1-C2 sin pulsar Validar."""

    try:
        outcome = service.run_header_draft(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible comprobar la carga del encabezado.",
        ) from error

    return BatchHeaderDraftProbeResponse.from_domain(outcome)



@router.post(
    "/{batch_id}/execution/general-data-draft-probe",
    response_model=BatchGeneralDataDraftProbeResponse,
)
def general_data_draft_probe(
    batch_id: UUID,
    payload: BatchGeneralDataDraftProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchGeneralDataDraftProbeResponse:
    try:
        outcome = service.run_general_data_draft(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    return BatchGeneralDataDraftProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/general-completion-draft-probe",
    response_model=BatchGeneralCompletionDraftProbeResponse,
)
def general_completion_draft_probe(
    batch_id: UUID,
    payload: BatchGeneralCompletionDraftProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchGeneralCompletionDraftProbeResponse:
    """Completa C3-C4 sin pulsar la validación general ni Guardar."""

    try:
        outcome = service.run_general_completion_draft(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible comprobar la carga C4.",
        ) from error

    return BatchGeneralCompletionDraftProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/general-validation-probe",
    response_model=BatchGeneralValidationProbeResponse,
)
def general_validation_probe(
    batch_id: UUID,
    payload: BatchGeneralValidationProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchGeneralValidationProbeResponse:
    """Valida C3-C4 y confirma Guardar sin pulsarlo."""

    try:
        outcome = service.run_general_validation(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible comprobar la validación general.",
        ) from error

    return BatchGeneralValidationProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/contract-save-probe",
    response_model=BatchContractSaveProbeResponse,
)
def contract_save_probe(
    batch_id: UUID,
    payload: BatchContractSaveProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchContractSaveProbeResponse:
    """Guarda un contrato autorizado y confirma la etapa de supervisor."""

    try:
        outcome = service.run_contract_save(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
            confirmation=payload.confirmation,
            allow_test_values=payload.allow_test_values,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible guardar el contrato autorizado.",
        ) from error

    return BatchContractSaveProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/contract-supervisor-link-probe",
    response_model=BatchContractSupervisorLinkProbeResponse,
)
def contract_supervisor_link_probe(
    batch_id: UUID,
    payload: BatchContractSupervisorLinkProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchContractSupervisorLinkProbeResponse:
    """Guarda un contrato y vincula su supervisor interno."""

    try:
        outcome = service.run_contract_supervisor_link(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
            confirmation=payload.confirmation,
            allow_test_values=payload.allow_test_values,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible guardar el contrato y vincular "
                "su supervisor."
            ),
        ) from error

    return BatchContractSupervisorLinkProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/contract-availability-link-probe",
    response_model=BatchContractAvailabilityLinkProbeResponse,
)
def contract_availability_link_probe(
    batch_id: UUID,
    payload: BatchContractAvailabilityLinkProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchContractAvailabilityLinkProbeResponse:
    """Guarda contrato, vincula supervisor y disponibilidad CDP."""

    try:
        outcome = service.run_contract_availability_link(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
            confirmation=payload.confirmation,
            allow_test_values=payload.allow_test_values,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible guardar el contrato, vincular el "
                "supervisor y vincular el CDP."
            ),
        ) from error

    return BatchContractAvailabilityLinkProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/contract-budget-register-link-probe",
    response_model=BatchContractBudgetRegisterLinkProbeResponse,
)
def contract_budget_register_link_probe(
    batch_id: UUID,
    payload: BatchContractBudgetRegisterLinkProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchContractBudgetRegisterLinkProbeResponse:
    """Guarda y vincula supervisor, CDP y registro presupuestal."""

    try:
        outcome = service.run_contract_budget_register_link(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
            confirmation=payload.confirmation,
            allow_test_values=payload.allow_test_values,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible guardar y vincular el registro "
                "presupuestal."
            ),
        ) from error

    return BatchContractBudgetRegisterLinkProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/contract-additional-dates-link-probe",
    response_model=BatchContractAdditionalDatesLinkProbeResponse,
)
def contract_additional_dates_link_probe(
    batch_id: UUID,
    payload: BatchContractAdditionalDatesLinkProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchContractAdditionalDatesLinkProbeResponse:
    """Guarda y vincula el contrato hasta fechas adicionales."""

    try:
        outcome = service.run_contract_additional_dates_link(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
            confirmation=payload.confirmation,
            allow_test_values=payload.allow_test_values,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible guardar y vincular las fechas "
                "adicionales del contrato."
            ),
        ) from error

    return BatchContractAdditionalDatesLinkProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution/header-validation-probe",
    response_model=BatchHeaderValidationProbeResponse,
)
def probe_batch_header_validation(
    batch_id: UUID,
    payload: BatchHeaderValidationProbeRequest,
    actor: Superuser,
    service: Annotated[
        BatchPortalProbeService,
        Depends(get_batch_portal_probe_service),
    ],
) -> BatchHeaderValidationProbeResponse:
    """Valida C1-C2 y comprueba C3 sin completar ni guardar."""

    try:
        outcome = service.run_header_validation(
            batch_id=batch_id,
            item_id=payload.item_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchPortalProbeBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchPortalProbeConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible comprobar la validación del encabezado.",
        ) from error

    return BatchHeaderValidationProbeResponse.from_domain(outcome)


@router.post(
    "/{batch_id}/execution",
    response_model=BatchExecutionStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_batch_execution(
    batch_id: UUID,
    actor: Superuser,
    service: Annotated[
        BatchExecutionService,
        Depends(get_batch_execution_service),
    ],
) -> BatchExecutionStatusResponse:
    try:
        batch = service.start(
            batch_id=batch_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        BatchExecutionBlockedError,
        BatchExecutionInProgressError,
        BatchNotReadyForExecutionError,
        BatchExecutionStateError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible iniciar la ejecución del lote.",
        ) from error
    return BatchExecutionStatusResponse.from_domain(
        batch,
        active_in_process=service.is_active(batch.batch_id),
    )


@router.get(
    "/{batch_id}/execution",
    response_model=BatchExecutionStatusResponse,
)
def get_batch_execution(
    batch_id: UUID,
    actor: Superuser,
    service: Annotated[
        BatchExecutionService,
        Depends(get_batch_execution_service),
    ],
) -> BatchExecutionStatusResponse:
    try:
        batch = service.get(
            batch_id=batch_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar el progreso del lote.",
        ) from error
    return BatchExecutionStatusResponse.from_domain(
        batch,
        active_in_process=service.is_active(batch.batch_id),
    )


@router.post(
    "/{batch_id}/cancel",
    response_model=BatchResponse,
)
def cancel_ready_batch(
    batch_id: UUID,
    actor: Superuser,
    service: Annotated[
        BatchExecutionService,
        Depends(get_batch_execution_service),
    ],
) -> BatchResponse:
    try:
        batch = service.cancel(
            batch_id=batch_id,
            dependency=actor.dependency,
        )
    except BatchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except BatchExecutionStateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except BatchRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible cancelar el lote.",
        ) from error
    return BatchResponse.from_domain(batch)
