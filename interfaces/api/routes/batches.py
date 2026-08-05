from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from application.ports.execution_repository import ExecutionRepositoryError
from application.ports.execution_evidence_repository import (
    ExecutionEvidenceRepositoryError,
)
from application.services.batch_creation_service import BatchCreationService
from application.services.controlled_batch_contract_execution_service import (
    ControlledBatchContractExecutionService,
)
from application.services.batch_execution_service import BatchExecutionService
from application.services.batch_portal_probe_service import (
    BatchPortalProbeService,
)
from application.services.institutional_test_plan_service import (
    InstitutionalTestPlanService,
)
from domain.errors.batch_contract_execution_errors import (
    BatchContractExecutionBlockedError,
    BatchContractExecutionConfirmationError,
    BatchContractExecutionIdentityError,
    BatchContractExecutionInProgressError,
    BatchContractExecutionStateError,
    BatchContractItemNotFoundError,
)
from domain.enums import ExecutionMode
from domain.errors.execution_evidence_errors import (
    ExecutionEvidenceContextError,
    ExecutionEvidenceNotFoundError,
)
from domain.errors.real_write_authorization_errors import (
    RealWriteAuthorizationConfirmationError,
    RealWriteAuthorizationConsumedError,
    RealWriteAuthorizationContextError,
    RealWriteAuthorizationDisabledError,
    RealWriteAuthorizationExpiredError,
    RealWriteAuthorizationInvalidError,
    RealWriteAuthorizationNotFoundError,
    RealWriteAuthorizationRepositoryError,
    RealWriteAuthorizationRequiredError,
    RealWriteAuthorizationRevocationConfirmationError,
    RealWriteAuthorizationRevokedError,
)
from domain.errors.institutional_test_plan_errors import (
    InstitutionalTestPlanCancelledError,
    InstitutionalTestPlanConfirmationError,
    InstitutionalTestPlanConsumedError,
    InstitutionalTestPlanContextError,
    InstitutionalTestPlanDiagnosticExpiredError,
    InstitutionalTestPlanDiagnosticRequiredError,
    InstitutionalTestPlanDisabledError,
    InstitutionalTestPlanExpiredError,
    InstitutionalTestPlanNotArmedError,
    InstitutionalTestPlanNotFoundError,
    InstitutionalTestPlanRepositoryError,
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
    get_institutional_test_plan_service,
)
from interfaces.api.schemas.batches import (
    BatchContractExecutionPreflightResponse,
    BatchContractExecutionRequest,
    BatchContractExecutionResponse,
    ContractExecutionEvidenceResponse,
    RealWriteAuthorizationIssueRequest,
    RealWriteAuthorizationRevokeRequest,
    RealWriteAuthorizationResponse,
    InstitutionalTestPlanArmRequest,
    InstitutionalTestPlanCancelRequest,
    InstitutionalTestPlanCreateRequest,
    InstitutionalTestPlanDiagnosticRequest,
    InstitutionalTestPlanResponse,
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
        ControlledBatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
    mode: ExecutionMode = Query(default=ExecutionMode.DRY_RUN),
) -> BatchContractExecutionPreflightResponse:
    try:
        preflight = service.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            mode=mode,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
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
        ExecutionEvidenceRepositoryError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible comprobar el contrato seleccionado."
            ),
        ) from error

    return BatchContractExecutionPreflightResponse.from_domain(preflight)


@router.post(
    "/{batch_id}/contracts/{item_id}/execution/authorization",
    response_model=RealWriteAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_selected_contract_real_write_authorization(
    batch_id: UUID,
    item_id: UUID,
    payload: RealWriteAuthorizationIssueRequest,
    actor: Superuser,
    service: Annotated[
        ControlledBatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
) -> RealWriteAuthorizationResponse:
    try:
        issued = service.issue_real_write_authorization(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            confirmation=payload.confirmation,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
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
    except RealWriteAuthorizationConfirmationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": error.code,
                "message": str(error),
                "required_confirmation": error.required_confirmation,
            },
        ) from error
    except RealWriteAuthorizationDisabledError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": error.code,
                "message": str(error),
            },
        ) from error
    except BatchContractExecutionBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REAL_WRITE_AUTHORIZATION_BLOCKED",
                "message": str(error),
                "issues": [
                    {"code": code, "message": message}
                    for code, message in error.issues
                ],
            },
        ) from error
    except (
        BatchRepositoryError,
        ExecutionRepositoryError,
        RealWriteAuthorizationRepositoryError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible emitir la autorización temporal."
            ),
        ) from error

    return RealWriteAuthorizationResponse.from_issued(issued)


@router.get(
    "/{batch_id}/contracts/{item_id}/execution/authorization",
    response_model=RealWriteAuthorizationResponse,
)
def get_selected_contract_real_write_authorization(
    batch_id: UUID,
    item_id: UUID,
    actor: Superuser,
    service: Annotated[
        ControlledBatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
) -> RealWriteAuthorizationResponse:
    try:
        authorization, events = service.get_real_write_authorization(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
        )
        preflight = service.preflight(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            mode=ExecutionMode.REAL,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
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
        RealWriteAuthorizationRepositoryError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible consultar la autorización temporal."
            ),
        ) from error

    return RealWriteAuthorizationResponse.from_status(
        authorization=authorization,
        events=events,
        batch_id=batch_id,
        item_id=item_id,
        contract_number=preflight.item.contract.contract_number,
        dependency=preflight.batch.dependency,
    )


@router.delete(
    "/{batch_id}/contracts/{item_id}/execution/authorization",
    response_model=RealWriteAuthorizationResponse,
)
def revoke_selected_contract_real_write_authorization(
    batch_id: UUID,
    item_id: UUID,
    payload: RealWriteAuthorizationRevokeRequest,
    actor: Superuser,
    service: Annotated[
        ControlledBatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
) -> RealWriteAuthorizationResponse:
    try:
        authorization, events = (
            service.revoke_real_write_authorization(
                batch_id=batch_id,
                item_id=item_id,
                dependency=actor.dependency,
                confirmation=payload.confirmation,
                actor_username=actor.username,
                actor_user_id=actor.user_id,
            )
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
    except RealWriteAuthorizationRevocationConfirmationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": error.code,
                "message": str(error),
                "required_confirmation": error.required_confirmation,
            },
        ) from error
    except RealWriteAuthorizationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": error.code,
                "message": str(error),
            },
        ) from error
    except (
        RealWriteAuthorizationExpiredError,
        RealWriteAuthorizationConsumedError,
        RealWriteAuthorizationRevokedError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": error.code,
                "message": str(error),
            },
        ) from error
    except RealWriteAuthorizationContextError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": error.code,
                "message": (
                    "La autorización temporal no pertenece al contexto "
                    "solicitado."
                ),
            },
        ) from error
    except (
        BatchRepositoryError,
        ExecutionRepositoryError,
        RealWriteAuthorizationRepositoryError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible revocar la autorización temporal.",
        ) from error

    return RealWriteAuthorizationResponse.from_status(
        authorization=authorization,
        events=events,
        batch_id=batch_id,
        item_id=item_id,
        contract_number=authorization.contract_number,
        dependency=authorization.dependency,
    )



def _institutional_plan_blocked_error(
    error: BatchContractExecutionBlockedError,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "INSTITUTIONAL_TEST_PLAN_BLOCKED",
            "message": str(error),
            "issues": [
                {"code": code, "message": message}
                for code, message in error.issues
            ],
        },
    )


def _institutional_plan_error(error: Exception) -> HTTPException:
    if isinstance(error, InstitutionalTestPlanNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": error.code, "message": str(error)},
        )
    if isinstance(error, InstitutionalTestPlanContextError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": error.code, "message": str(error)},
        )
    if isinstance(error, InstitutionalTestPlanRepositoryError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": error.code, "message": str(error)},
        )
    if isinstance(error, InstitutionalTestPlanConfirmationError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": error.code,
                "message": str(error),
                "required_confirmation": error.required_confirmation,
            },
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": getattr(
                error,
                "code",
                "INSTITUTIONAL_TEST_PLAN_ERROR",
            ),
            "message": str(error),
        },
    )


@router.post(
    "/{batch_id}/contracts/{item_id}/execution/institutional-plan",
    response_model=InstitutionalTestPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_selected_contract_institutional_plan(
    batch_id: UUID,
    item_id: UUID,
    payload: InstitutionalTestPlanCreateRequest,
    actor: Superuser,
    service: Annotated[
        InstitutionalTestPlanService,
        Depends(get_institutional_test_plan_service),
    ],
) -> InstitutionalTestPlanResponse:
    try:
        plan = service.create(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
            confirmation=payload.confirmation,
        )
        events = service.list_events(
            batch_id=batch_id,
            item_id=item_id,
        )
    except (
        InstitutionalTestPlanDisabledError,
        InstitutionalTestPlanConfirmationError,
        InstitutionalTestPlanRepositoryError,
        BatchContractExecutionBlockedError,
        BatchNotFoundError,
        BatchContractItemNotFoundError,
    ) as error:
        if isinstance(error, BatchNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        if isinstance(error, BatchContractItemNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        if isinstance(error, BatchContractExecutionBlockedError):
            raise _institutional_plan_blocked_error(error) from error
        raise _institutional_plan_error(error) from error

    return InstitutionalTestPlanResponse.from_domain(
        plan=plan,
        events=events,
        enabled=service.enabled,
        batch_id=batch_id,
        item_id=item_id,
        contract_number=plan.contract_number,
        dependency=plan.dependency,
    )


@router.get(
    "/{batch_id}/contracts/{item_id}/execution/institutional-plan",
    response_model=InstitutionalTestPlanResponse,
)
def get_selected_contract_institutional_plan(
    batch_id: UUID,
    item_id: UUID,
    actor: Superuser,
    service: Annotated[
        InstitutionalTestPlanService,
        Depends(get_institutional_test_plan_service),
    ],
) -> InstitutionalTestPlanResponse:
    try:
        plan, events, contract_number, dependency = service.status(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
        )
    except (BatchNotFoundError, BatchContractItemNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except InstitutionalTestPlanRepositoryError as error:
        raise _institutional_plan_error(error) from error

    return InstitutionalTestPlanResponse.from_domain(
        plan=plan,
        events=events,
        enabled=service.enabled,
        batch_id=batch_id,
        item_id=item_id,
        contract_number=contract_number,
        dependency=dependency,
    )


@router.post(
    "/{batch_id}/contracts/{item_id}/execution/institutional-plan/diagnostic",
    response_model=InstitutionalTestPlanResponse,
)
def diagnose_selected_contract_institutional_plan(
    batch_id: UUID,
    item_id: UUID,
    payload: InstitutionalTestPlanDiagnosticRequest,
    actor: Superuser,
    service: Annotated[
        InstitutionalTestPlanService,
        Depends(get_institutional_test_plan_service),
    ],
) -> InstitutionalTestPlanResponse:
    try:
        plan = service.run_read_only_diagnostic(
            plan_id=payload.plan_id,
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
        )
        events = service.list_events(
            batch_id=batch_id,
            item_id=item_id,
        )
    except BatchContractExecutionBlockedError as error:
        raise _institutional_plan_blocked_error(error) from error
    except (
        InstitutionalTestPlanDisabledError,
        InstitutionalTestPlanNotFoundError,
        InstitutionalTestPlanContextError,
        InstitutionalTestPlanExpiredError,
        InstitutionalTestPlanCancelledError,
        InstitutionalTestPlanConsumedError,
        InstitutionalTestPlanRepositoryError,
        BatchPortalProbeBlockedError,
        BatchPortalProbeConfigurationError,
    ) as error:
        if isinstance(
            error,
            (BatchPortalProbeBlockedError, BatchPortalProbeConfigurationError),
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "INSTITUTIONAL_TEST_PLAN_DIAGNOSTIC_BLOCKED",
                    "message": str(error),
                },
            ) from error
        raise _institutional_plan_error(error) from error

    return InstitutionalTestPlanResponse.from_domain(
        plan=plan,
        events=events,
        enabled=service.enabled,
        batch_id=batch_id,
        item_id=item_id,
        contract_number=plan.contract_number,
        dependency=plan.dependency,
    )


@router.post(
    "/{batch_id}/contracts/{item_id}/execution/institutional-plan/arm",
    response_model=InstitutionalTestPlanResponse,
)
def arm_selected_contract_institutional_plan(
    batch_id: UUID,
    item_id: UUID,
    payload: InstitutionalTestPlanArmRequest,
    actor: Superuser,
    service: Annotated[
        InstitutionalTestPlanService,
        Depends(get_institutional_test_plan_service),
    ],
) -> InstitutionalTestPlanResponse:
    try:
        plan = service.arm(
            plan_id=payload.plan_id,
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
            confirmation=payload.confirmation,
        )
        events = service.list_events(
            batch_id=batch_id,
            item_id=item_id,
        )
    except BatchContractExecutionBlockedError as error:
        raise _institutional_plan_blocked_error(error) from error
    except (
        InstitutionalTestPlanDisabledError,
        InstitutionalTestPlanConfirmationError,
        InstitutionalTestPlanNotFoundError,
        InstitutionalTestPlanContextError,
        InstitutionalTestPlanExpiredError,
        InstitutionalTestPlanCancelledError,
        InstitutionalTestPlanConsumedError,
        InstitutionalTestPlanDiagnosticRequiredError,
        InstitutionalTestPlanDiagnosticExpiredError,
        InstitutionalTestPlanRepositoryError,
    ) as error:
        raise _institutional_plan_error(error) from error

    return InstitutionalTestPlanResponse.from_domain(
        plan=plan,
        events=events,
        enabled=service.enabled,
        batch_id=batch_id,
        item_id=item_id,
        contract_number=plan.contract_number,
        dependency=plan.dependency,
    )


@router.delete(
    "/{batch_id}/contracts/{item_id}/execution/institutional-plan",
    response_model=InstitutionalTestPlanResponse,
)
def cancel_selected_contract_institutional_plan(
    batch_id: UUID,
    item_id: UUID,
    payload: InstitutionalTestPlanCancelRequest,
    actor: Superuser,
    service: Annotated[
        InstitutionalTestPlanService,
        Depends(get_institutional_test_plan_service),
    ],
) -> InstitutionalTestPlanResponse:
    try:
        plan = service.cancel(
            plan_id=payload.plan_id,
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
            confirmation=payload.confirmation,
        )
        events = service.list_events(
            batch_id=batch_id,
            item_id=item_id,
        )
    except (
        InstitutionalTestPlanConfirmationError,
        InstitutionalTestPlanNotFoundError,
        InstitutionalTestPlanContextError,
        InstitutionalTestPlanExpiredError,
        InstitutionalTestPlanCancelledError,
        InstitutionalTestPlanConsumedError,
        InstitutionalTestPlanRepositoryError,
    ) as error:
        raise _institutional_plan_error(error) from error

    return InstitutionalTestPlanResponse.from_domain(
        plan=plan,
        events=events,
        enabled=service.enabled,
        batch_id=batch_id,
        item_id=item_id,
        contract_number=plan.contract_number,
        dependency=plan.dependency,
    )


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
        ControlledBatchContractExecutionService,
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
            mode=payload.mode,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
            authorization_token=payload.authorization_token,
            institutional_plan_id=payload.institutional_plan_id,
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
    except RealWriteAuthorizationConfirmationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": error.code,
                "message": str(error),
                "required_confirmation": error.required_confirmation,
            },
        ) from error
    except (
        RealWriteAuthorizationRequiredError,
        RealWriteAuthorizationExpiredError,
        RealWriteAuthorizationConsumedError,
        RealWriteAuthorizationRevokedError,
        RealWriteAuthorizationDisabledError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": error.code,
                "message": str(error),
            },
        ) from error
    except (
        RealWriteAuthorizationInvalidError,
        RealWriteAuthorizationContextError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": error.code,
                "message": (
                    "La autorización temporal no es válida para "
                    "esta operación."
                ),
            },
        ) from error
    except RealWriteAuthorizationRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible validar la autorización temporal."
            ),
        ) from error
    except (
        InstitutionalTestPlanNotFoundError,
        InstitutionalTestPlanExpiredError,
        InstitutionalTestPlanCancelledError,
        InstitutionalTestPlanConsumedError,
        InstitutionalTestPlanNotArmedError,
        InstitutionalTestPlanDiagnosticRequiredError,
        InstitutionalTestPlanDiagnosticExpiredError,
        InstitutionalTestPlanDisabledError,
    ) as error:
        raise _institutional_plan_error(error) from error
    except InstitutionalTestPlanContextError as error:
        raise _institutional_plan_error(error) from error
    except InstitutionalTestPlanRepositoryError as error:
        raise _institutional_plan_error(error) from error
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
        ExecutionEvidenceRepositoryError,
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
        ControlledBatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
    mode: ExecutionMode = Query(default=ExecutionMode.DRY_RUN),
) -> BatchContractExecutionResponse:
    try:
        result = service.status(
            batch_id=batch_id,
            item_id=item_id,
            dependency=actor.dependency,
            mode=mode,
            actor_username=actor.username,
            actor_user_id=actor.user_id,
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
        ExecutionEvidenceRepositoryError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fue posible consultar el checkpoint del contrato."
            ),
        ) from error

    return BatchContractExecutionResponse.from_domain(result)


@router.get(
    "/{batch_id}/contracts/{item_id}/execution/evidence/{correlation_id}",
    response_model=ContractExecutionEvidenceResponse,
)
def get_selected_contract_execution_evidence(
    batch_id: UUID,
    item_id: UUID,
    correlation_id: UUID,
    actor: Superuser,
    service: Annotated[
        ControlledBatchContractExecutionService,
        Depends(get_batch_contract_execution_service),
    ],
) -> ContractExecutionEvidenceResponse:
    try:
        evidence = service.get_evidence(
            batch_id=batch_id,
            item_id=item_id,
            correlation_id=correlation_id,
            dependency=actor.dependency,
        )
    except ExecutionEvidenceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ExecutionEvidenceContextError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ExecutionEvidenceRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar las evidencias de ejecución.",
        ) from error

    return ContractExecutionEvidenceResponse.from_domain(evidence)


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
