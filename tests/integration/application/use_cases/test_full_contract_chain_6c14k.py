from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from adapters.persistence.sqlite import SQLiteExecutionRepository
from application.dto import PortalStepVerification, PortalVerificationStatus
from application.ports import OpenedContractPortalSession
from application.use_cases import ExecuteContractInSession
from application.workflow import (
    ExecutionCheckpointService,
    completed_stage_count,
    project_contract_chain,
)
from domain.enums import ContractStep, ContractorNature, ExecutionStatus
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


@dataclass
class RecordingPortal:
    applied_steps: set[ContractStep] = field(default_factory=set)
    execute_calls: list[ContractStep] = field(default_factory=list)
    verify_calls: list[ContractStep] = field(default_factory=list)

    def execute_step(self, step: ContractStep, contract: ContractData) -> None:
        self.execute_calls.append(step)
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
            message=f"Postcondición confirmada para {step.value}.",
        )

    def recover(self) -> None:
        return None


@dataclass
class RecordingSessionFactory:
    portal: RecordingPortal
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


def institutional_contract_70_2026() -> ContractData:
    return ContractData(
        contract_number="70-2026",
        dependency="Adquisiciones",
        contractor=ContractorData(
            document_number="900469775-8",
            nature=ContractorNature.LEGAL_ENTITY,
        ),
        project_code="I-23021-2026",
        object_description=(
            "Servicio de software para la administración y Control del "
            "Sistema Integrado de Gestión de la Institución para el año "
            "2026."
        ),
        signing_date=date(2026, 8, 4),
        starting_date=date(2026, 8, 4),
        amount=Decimal("1"),
        term_days=365,
        process_type="Contratacion Directa",
        procedure="Sin Pluralidad De Oferentes",
        contract_type="Contrato de Prestación de Servicios",
        budget=BudgetData(
            year=2026,
            item="IDEA-2026 - RECURSOS CONVENIO IDEA",
            subsector="Tecnología",
            cdp_code="700",
            budget_register_number="10",
            budget_register_date=date(2026, 8, 4),
            gross_total=Decimal("1"),
        ),
        supervisor=SupervisorData(
            document_number="71693738",
            supervisor_type="Interno",
        ),
        secop_url=(
            "https://community.secop.gov.co/Public/Tendering/"
            "ContractNoticePhases/View?PPI=CO1.PPI.45062499&"
            "isFromPublicArea=True&isModal=False"
        ),
        guarantee_approval_date=date(2026, 8, 4),
        website_publication_date=date(2026, 8, 4),
        secop_publication_date=date(2026, 8, 4),
    )


def test_should_execute_c1_c13_for_institutional_contract_in_one_session(
    tmp_path: Path,
) -> None:
    repository = SQLiteExecutionRepository(tmp_path / "full-chain.db")
    checkpoints = ExecutionCheckpointService(repository)
    portal = RecordingPortal()
    sessions = RecordingSessionFactory(portal)
    use_case = ExecuteContractInSession(
        sessions=sessions,
        checkpoints=checkpoints,
    )

    result = use_case.execute(contract=institutional_contract_70_2026())

    assert result.execution.status is ExecutionStatus.COMPLETED
    assert result.execution.last_completed_step is ContractStep.COMPLETED
    assert sessions.open_calls == ["Adquisiciones"]
    assert sessions.close_calls == 1
    assert portal.execute_calls == [
        ContractStep.ASSISTANT_OPENED,
        ContractStep.HEADER_COMPLETED,
        ContractStep.HEADER_VALIDATED,
        ContractStep.GENERAL_DATA_COMPLETED,
        ContractStep.CONTRACT_SAVED,
        ContractStep.SUPERVISOR_LINKED,
        ContractStep.AVAILABILITY_LINKED,
        ContractStep.BUDGET_REGISTER_LINKED,
        ContractStep.ADDITIONAL_DATES_LINKED,
    ]
    assert [transition.step for transition in result.transitions] == [
        ContractStep.INPUT_VALIDATED,
        *portal.execute_calls,
        ContractStep.COMPLETED,
    ]

    chain = project_contract_chain(
        last_completed_step=result.execution.last_completed_step,
        current_step=result.execution.current_step,
        last_failed_step=result.execution.last_failed_step,
    )
    assert completed_stage_count(chain) == 13
