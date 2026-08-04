from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from adapters.persistence.sqlite import SQLiteExecutionRepository
from application.dto import PortalStepVerification, PortalVerificationStatus
from application.ports import OpenedContractPortalSession
from application.use_cases import ExecuteContractInSession
from application.workflow import ExecutionCheckpointService
from domain.enums import ContractStep, ContractorNature, ExecutionStatus
from domain.errors import PortalTimeoutError
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


@dataclass
class FakePortal:
    applied_steps: set[ContractStep] = field(default_factory=set)
    execute_calls: list[ContractStep] = field(default_factory=list)
    verify_calls: list[ContractStep] = field(default_factory=list)
    errors: dict[ContractStep, list[BaseException]] = field(default_factory=dict)
    recover_calls: int = 0

    def execute_step(self, step: ContractStep, contract: ContractData) -> None:
        self.execute_calls.append(step)
        errors = self.errors.get(step)
        if errors:
            raise errors.pop(0)
        self.applied_steps.add(step)

    def verify_step(
        self,
        step: ContractStep,
        contract: ContractData,
    ) -> PortalStepVerification:
        self.verify_calls.append(step)
        return PortalStepVerification(
            step=step,
            status=(
                PortalVerificationStatus.CONFIRMED
                if step in self.applied_steps
                else PortalVerificationStatus.NOT_APPLIED
            ),
        )

    def recover(self) -> None:
        self.recover_calls += 1


@dataclass
class FakeSessionFactory:
    portal: FakePortal
    open_calls: list[str] = field(default_factory=list)
    close_calls: int = 0

    @contextmanager
    def open(self, *, dependency: str):
        self.open_calls.append(dependency)
        try:
            yield OpenedContractPortalSession(
                portal=self.portal,
                profile="v2026_07",
            )
        finally:
            self.close_calls += 1


def build_contract() -> ContractData:
    return ContractData(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
        contractor=ContractorData(
            document_number="900469775-8",
            nature=ContractorNature.LEGAL_ENTITY,
        ),
        project_code="I-23021-2026",
        object_description="Servicio institucional.",
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
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Supervisor",
        ),
    )


def build_use_case(tmp_path: Path, portal: FakePortal):
    repository = SQLiteExecutionRepository(tmp_path / "session.db")
    checkpoints = ExecutionCheckpointService(repository)
    sessions = FakeSessionFactory(portal)
    use_case = ExecuteContractInSession(
        sessions=sessions,
        checkpoints=checkpoints,
    )
    return checkpoints, sessions, use_case


def test_should_use_one_portal_session_for_complete_contract(
    tmp_path: Path,
) -> None:
    portal = FakePortal()
    _, sessions, use_case = build_use_case(tmp_path, portal)

    result = use_case.execute(contract=build_contract())

    assert result.completed
    assert result.execution.status is ExecutionStatus.COMPLETED
    assert sessions.open_calls == ["Proyectos Especiales"]
    assert sessions.close_calls == 1
    assert portal.execute_calls
    assert ContractStep.INPUT_VALIDATED not in portal.execute_calls


def test_should_close_session_when_processing_is_interrupted(
    tmp_path: Path,
) -> None:
    portal = FakePortal()
    portal.errors[ContractStep.ASSISTANT_OPENED] = [KeyboardInterrupt()]
    _, sessions, use_case = build_use_case(tmp_path, portal)

    with pytest.raises(KeyboardInterrupt):
        use_case.execute(contract=build_contract())

    assert sessions.close_calls == 1


def test_should_resume_existing_checkpoint_in_new_controlled_session(
    tmp_path: Path,
) -> None:
    portal = FakePortal()
    portal.errors[ContractStep.ASSISTANT_OPENED] = [
        PortalTimeoutError("El portal no respondió.")
    ]
    checkpoints, sessions, use_case = build_use_case(tmp_path, portal)
    contract = build_contract()

    interrupted = use_case.execute(contract=contract)
    assert interrupted.retry_pending
    execution_id: UUID = interrupted.execution.execution_id

    resumed = use_case.execute(
        contract=contract,
        execution_id=execution_id,
    )

    assert resumed.completed
    assert resumed.execution.attempt_count == 2
    assert sessions.close_calls == 2
    assert checkpoints.get(execution_id).status is ExecutionStatus.COMPLETED
