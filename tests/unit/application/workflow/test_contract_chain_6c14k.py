from application.workflow.contract_chain import (
    FULL_CONTRACT_CHAIN,
    ContractChainStageStatus,
    completed_stage_count,
    project_contract_chain,
    stage_metadata_for_checkpoint,
)
from domain.enums import ContractStep


def test_full_chain_should_define_c1_through_c13_once_and_in_order() -> None:
    assert len(FULL_CONTRACT_CHAIN) == 13
    assert [stage.code for stage in FULL_CONTRACT_CHAIN] == [
        f"C{index}" for index in range(1, 14)
    ]


def test_c8_should_be_the_first_persistent_irreversible_boundary() -> None:
    persistent = [
        stage
        for stage in FULL_CONTRACT_CHAIN
        if stage.persists_institutional_data
    ]
    irreversible = [
        stage
        for stage in FULL_CONTRACT_CHAIN
        if stage.irreversible_boundary
    ]

    assert persistent[0].code == "C8"
    assert [stage.code for stage in irreversible] == ["C8"]


def test_general_checkpoint_should_represent_c5_c6_and_c7() -> None:
    metadata = stage_metadata_for_checkpoint(
        ContractStep.GENERAL_DATA_COMPLETED
    )

    assert metadata["chain_stage_codes"] == ["C5", "C6", "C7"]
    assert metadata["chain_stage_count"] == 3
    assert metadata["chain_persists_institutional_data"] is False


def test_projection_should_show_atomic_general_group_as_active() -> None:
    stages = project_contract_chain(
        last_completed_step=ContractStep.HEADER_VALIDATED,
        current_step=ContractStep.GENERAL_DATA_COMPLETED,
    )
    by_code = {stage.code: stage for stage in stages}

    assert completed_stage_count(stages) == 4
    assert {
        by_code[code].status for code in ("C5", "C6", "C7")
    } == {ContractChainStageStatus.ACTIVE}
    assert by_code["C8"].status is ContractChainStageStatus.PENDING


def test_projection_should_mark_all_stages_complete_at_completed() -> None:
    stages = project_contract_chain(
        last_completed_step=ContractStep.COMPLETED,
    )

    assert completed_stage_count(stages) == 13
    assert {
        stage.status for stage in stages
    } == {ContractChainStageStatus.COMPLETED}
