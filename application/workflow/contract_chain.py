from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.enums import ContractStep


class ContractChainStageStatus(str, Enum):
    """Estado proyectado de una etapa funcional C1-C13."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ContractChainStage:
    """Etapa funcional visible de la cadena contractual completa.

    La máquina de estados persiste checkpoints técnicos. La cadena C1-C13
    proyecta esos checkpoints al recorrido funcional que fue comprobado de
    forma incremental contra Gestión Transparente.

    C5, C6 y C7 comparten el checkpoint ``GENERAL_DATA_COMPLETED`` porque el
    adaptador actual los ejecuta de manera atómica dentro de una misma sesión:
    carga de datos generales, carga complementaria y validación general.
    """

    code: str
    label: str
    checkpoint_step: ContractStep
    touches_portal: bool
    persists_institutional_data: bool
    irreversible_boundary: bool = False


@dataclass(frozen=True, slots=True)
class ContractChainStageProjection:
    code: str
    label: str
    checkpoint_step: ContractStep
    status: ContractChainStageStatus
    touches_portal: bool
    persists_institutional_data: bool
    irreversible_boundary: bool


FULL_CONTRACT_CHAIN: tuple[ContractChainStage, ...] = (
    ContractChainStage(
        code="C1",
        label="Validar datos de entrada",
        checkpoint_step=ContractStep.INPUT_VALIDATED,
        touches_portal=False,
        persists_institutional_data=False,
    ),
    ContractChainStage(
        code="C2",
        label="Abrir Asistente de Contratación",
        checkpoint_step=ContractStep.ASSISTANT_OPENED,
        touches_portal=True,
        persists_institutional_data=False,
    ),
    ContractChainStage(
        code="C3",
        label="Completar encabezado contractual",
        checkpoint_step=ContractStep.HEADER_COMPLETED,
        touches_portal=True,
        persists_institutional_data=False,
    ),
    ContractChainStage(
        code="C4",
        label="Validar encabezado y habilitar datos generales",
        checkpoint_step=ContractStep.HEADER_VALIDATED,
        touches_portal=True,
        persists_institutional_data=False,
    ),
    ContractChainStage(
        code="C5",
        label="Completar datos generales",
        checkpoint_step=ContractStep.GENERAL_DATA_COMPLETED,
        touches_portal=True,
        persists_institutional_data=False,
    ),
    ContractChainStage(
        code="C6",
        label="Completar información complementaria",
        checkpoint_step=ContractStep.GENERAL_DATA_COMPLETED,
        touches_portal=True,
        persists_institutional_data=False,
    ),
    ContractChainStage(
        code="C7",
        label="Validar formulario general y habilitar Guardar",
        checkpoint_step=ContractStep.GENERAL_DATA_COMPLETED,
        touches_portal=True,
        persists_institutional_data=False,
    ),
    ContractChainStage(
        code="C8",
        label="Guardar contrato",
        checkpoint_step=ContractStep.CONTRACT_SAVED,
        touches_portal=True,
        persists_institutional_data=True,
        irreversible_boundary=True,
    ),
    ContractChainStage(
        code="C9",
        label="Vincular supervisor interno",
        checkpoint_step=ContractStep.SUPERVISOR_LINKED,
        touches_portal=True,
        persists_institutional_data=True,
    ),
    ContractChainStage(
        code="C10",
        label="Vincular disponibilidad presupuestal (CDP)",
        checkpoint_step=ContractStep.AVAILABILITY_LINKED,
        touches_portal=True,
        persists_institutional_data=True,
    ),
    ContractChainStage(
        code="C11",
        label="Vincular registro presupuestal (RP)",
        checkpoint_step=ContractStep.BUDGET_REGISTER_LINKED,
        touches_portal=True,
        persists_institutional_data=True,
    ),
    ContractChainStage(
        code="C12",
        label="Vincular fechas adicionales",
        checkpoint_step=ContractStep.ADDITIONAL_DATES_LINKED,
        touches_portal=True,
        persists_institutional_data=True,
    ),
    ContractChainStage(
        code="C13",
        label="Confirmar finalización de la cadena",
        checkpoint_step=ContractStep.COMPLETED,
        touches_portal=False,
        persists_institutional_data=False,
    ),
)


_CHECKPOINT_ORDER: dict[ContractStep, int] = {
    ContractStep.PENDING: 0,
    ContractStep.INPUT_VALIDATED: 1,
    ContractStep.ASSISTANT_OPENED: 2,
    ContractStep.HEADER_COMPLETED: 3,
    ContractStep.HEADER_VALIDATED: 4,
    ContractStep.GENERAL_DATA_COMPLETED: 5,
    ContractStep.CONTRACT_SAVED: 6,
    ContractStep.SUPERVISOR_LINKED: 7,
    ContractStep.AVAILABILITY_LINKED: 8,
    ContractStep.BUDGET_REGISTER_LINKED: 9,
    ContractStep.ADDITIONAL_DATES_LINKED: 10,
    ContractStep.COMPLETED: 11,
}


def stages_for_checkpoint(
    step: ContractStep | None,
) -> tuple[ContractChainStage, ...]:
    if step is None:
        return ()
    return tuple(
        stage
        for stage in FULL_CONTRACT_CHAIN
        if stage.checkpoint_step is step
    )


def stage_metadata_for_checkpoint(
    step: ContractStep | None,
) -> dict[str, object]:
    stages = stages_for_checkpoint(step)
    return {
        "chain_stage_codes": [stage.code for stage in stages],
        "chain_stage_labels": [stage.label for stage in stages],
        "chain_stage_count": len(stages),
        "chain_persists_institutional_data": any(
            stage.persists_institutional_data for stage in stages
        ),
        "chain_irreversible_boundary": any(
            stage.irreversible_boundary for stage in stages
        ),
    }


def project_contract_chain(
    *,
    last_completed_step: ContractStep | None,
    current_step: ContractStep | None = None,
    last_failed_step: ContractStep | None = None,
) -> tuple[ContractChainStageProjection, ...]:
    """Proyecta checkpoints técnicos al recorrido funcional C1-C13."""

    completed_step = last_completed_step or ContractStep.PENDING
    completed_rank = _CHECKPOINT_ORDER.get(completed_step, 0)

    projections: list[ContractChainStageProjection] = []
    for stage in FULL_CONTRACT_CHAIN:
        stage_rank = _CHECKPOINT_ORDER[stage.checkpoint_step]

        if last_failed_step is stage.checkpoint_step:
            status = ContractChainStageStatus.FAILED
        elif current_step is stage.checkpoint_step:
            status = ContractChainStageStatus.ACTIVE
        elif completed_rank >= stage_rank:
            status = ContractChainStageStatus.COMPLETED
        else:
            status = ContractChainStageStatus.PENDING

        projections.append(
            ContractChainStageProjection(
                code=stage.code,
                label=stage.label,
                checkpoint_step=stage.checkpoint_step,
                status=status,
                touches_portal=stage.touches_portal,
                persists_institutional_data=(
                    stage.persists_institutional_data
                ),
                irreversible_boundary=stage.irreversible_boundary,
            )
        )

    return tuple(projections)


def completed_stage_count(
    projections: tuple[ContractChainStageProjection, ...],
) -> int:
    return sum(
        1
        for stage in projections
        if stage.status is ContractChainStageStatus.COMPLETED
    )
