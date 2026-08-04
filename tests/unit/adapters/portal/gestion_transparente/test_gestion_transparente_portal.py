<<<<<<< HEAD
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import pytest

from adapters.portal.gestion_transparente import (
    GestionTransparentePortal,
    PortalVerificationMismatchError,
    UnsupportedPortalStepError,
)
from application.dto import (
    PortalStepVerification,
    PortalVerificationStatus,
)
from domain.enums import (
    ContractStep,
    ContractorNature,
)
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


@dataclass
class RecordingComponent:
    """
    Componente simulado que implementa todos los contratos necesarios.

    Cada dependencia recibe una instancia diferente, permitiendo
    comprobar a cuál componente fue despachada la etapa.
    """

    name: str
    calls: list[str] = field(default_factory=list)

    verification_overrides: dict[
        str,
        ContractStep,
    ] = field(default_factory=dict)

    def _record(
        self,
        operation: str,
    ) -> None:
        self.calls.append(operation)

    def _verification(
        self,
        operation: str,
        expected_step: ContractStep,
    ) -> PortalStepVerification:
        self._record(operation)

        returned_step = self.verification_overrides.get(
            operation,
            expected_step,
        )

        return PortalStepVerification(
            step=returned_step,
            status=PortalVerificationStatus.CONFIRMED,
            message=f"{operation} confirmado",
            metadata={
                "component": self.name,
            },
        )

    # Asistente

    def open(
        self,
        contract: ContractData,
    ) -> None:
        self._record("open")

    def verify_open(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_open",
            ContractStep.ASSISTANT_OPENED,
        )

    # Cabecera

    def complete_header(
        self,
        contract: ContractData,
    ) -> None:
        self._record("complete_header")

    def verify_header_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_header_completed",
            ContractStep.HEADER_COMPLETED,
        )

    def validate_header(
        self,
        contract: ContractData,
    ) -> None:
        self._record("validate_header")

    def verify_header_validated(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_header_validated",
            ContractStep.HEADER_VALIDATED,
        )

    # Datos generales

    def complete_general_data(
        self,
        contract: ContractData,
    ) -> None:
        self._record("complete_general_data")

    def verify_general_data_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_general_data_completed",
            ContractStep.GENERAL_DATA_COMPLETED,
        )

    def save_contract(
        self,
        contract: ContractData,
    ) -> None:
        self._record("save_contract")

    def verify_contract_saved(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_contract_saved",
            ContractStep.CONTRACT_SAVED,
        )

    # Supervisor

    def link_supervisor(
        self,
        contract: ContractData,
    ) -> None:
        self._record("link_supervisor")

    def verify_supervisor_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_supervisor_linked",
            ContractStep.SUPERVISOR_LINKED,
        )

    # Disponibilidad

    def link_availability(
        self,
        contract: ContractData,
    ) -> None:
        self._record("link_availability")

    def verify_availability_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_availability_linked",
            ContractStep.AVAILABILITY_LINKED,
        )

    # Registro presupuestal

    def link_budget_register(
        self,
        contract: ContractData,
    ) -> None:
        self._record("link_budget_register")

    def verify_budget_register_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_budget_register_linked",
            ContractStep.BUDGET_REGISTER_LINKED,
        )

    # Fechas adicionales

    def link_additional_dates(
        self,
        contract: ContractData,
    ) -> None:
        self._record("link_additional_dates")

    def verify_additional_dates_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_additional_dates_linked",
            ContractStep.ADDITIONAL_DATES_LINKED,
        )

    # Recuperación

    def recover(self) -> None:
        self._record("recover")


def build_contract() -> ContractData:
    contractor = ContractorData(
        document_number="900469775-8",
        nature=ContractorNature.LEGAL_ENTITY,
    )

    supervisor = SupervisorData(
        document_number="71693738",
        supervisor_type="Supervisor",
    )

    budget = BudgetData(
        year=2026,
        item="IDEA-2026",
        subsector="Tecnología",
        cdp_code="235097",
        gross_total=Decimal("1476190"),
    )

    return ContractData(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
        contractor=contractor,
        project_code="I-23021-2026",
        object_description="Servicio institucional.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1476190"),
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=budget,
        supervisor=supervisor,
    )


def create_portal():
    components = {
        "assistant": RecordingComponent(
            "assistant"
        ),
        "header": RecordingComponent(
            "header"
        ),
        "general_data": RecordingComponent(
            "general_data"
        ),
        "supervisor": RecordingComponent(
            "supervisor"
        ),
        "availability": RecordingComponent(
            "availability"
        ),
        "budget_register": RecordingComponent(
            "budget_register"
        ),
        "additional_dates": RecordingComponent(
            "additional_dates"
        ),
        "recovery": RecordingComponent(
            "recovery"
        ),
    }

    portal = GestionTransparentePortal(
        assistant=components["assistant"],
        header=components["header"],
        general_data=components["general_data"],
        supervisor=components["supervisor"],
        availability=components["availability"],
        budget_register=components["budget_register"],
        additional_dates=components[
            "additional_dates"
        ],
        recovery=components["recovery"],
    )

    return portal, components


EXECUTION_CASES = (
    (
        ContractStep.ASSISTANT_OPENED,
        "assistant",
        "open",
    ),
    (
        ContractStep.HEADER_COMPLETED,
        "header",
        "complete_header",
    ),
    (
        ContractStep.HEADER_VALIDATED,
        "header",
        "validate_header",
    ),
    (
        ContractStep.GENERAL_DATA_COMPLETED,
        "general_data",
        "complete_general_data",
    ),
    (
        ContractStep.CONTRACT_SAVED,
        "general_data",
        "save_contract",
    ),
    (
        ContractStep.SUPERVISOR_LINKED,
        "supervisor",
        "link_supervisor",
    ),
    (
        ContractStep.AVAILABILITY_LINKED,
        "availability",
        "link_availability",
    ),
    (
        ContractStep.BUDGET_REGISTER_LINKED,
        "budget_register",
        "link_budget_register",
    ),
    (
        ContractStep.ADDITIONAL_DATES_LINKED,
        "additional_dates",
        "link_additional_dates",
    ),
)


VERIFICATION_CASES = (
    (
        ContractStep.ASSISTANT_OPENED,
        "assistant",
        "verify_open",
    ),
    (
        ContractStep.HEADER_COMPLETED,
        "header",
        "verify_header_completed",
    ),
    (
        ContractStep.HEADER_VALIDATED,
        "header",
        "verify_header_validated",
    ),
    (
        ContractStep.GENERAL_DATA_COMPLETED,
        "general_data",
        "verify_general_data_completed",
    ),
    (
        ContractStep.CONTRACT_SAVED,
        "general_data",
        "verify_contract_saved",
    ),
    (
        ContractStep.SUPERVISOR_LINKED,
        "supervisor",
        "verify_supervisor_linked",
    ),
    (
        ContractStep.AVAILABILITY_LINKED,
        "availability",
        "verify_availability_linked",
    ),
    (
        ContractStep.BUDGET_REGISTER_LINKED,
        "budget_register",
        "verify_budget_register_linked",
    ),
    (
        ContractStep.ADDITIONAL_DATES_LINKED,
        "additional_dates",
        "verify_additional_dates_linked",
    ),
)


@pytest.mark.parametrize(
    (
        "step",
        "component_name",
        "expected_operation",
    ),
    EXECUTION_CASES,
)
def test_should_dispatch_execution_to_expected_component(
    step: ContractStep,
    component_name: str,
    expected_operation: str,
) -> None:
    portal, components = create_portal()
    contract = build_contract()

    portal.execute_step(
        step,
        contract,
    )

    assert components[
        component_name
    ].calls == [
        expected_operation
    ]

    for name, component in components.items():
        if name in {
            component_name,
        }:
            continue

        assert component.calls == []


@pytest.mark.parametrize(
    (
        "step",
        "component_name",
        "expected_operation",
    ),
    VERIFICATION_CASES,
)
def test_should_dispatch_verification_to_expected_component(
    step: ContractStep,
    component_name: str,
    expected_operation: str,
) -> None:
    portal, components = create_portal()
    contract = build_contract()

    verification = portal.verify_step(
        step,
        contract,
    )

    assert verification.step is step
    assert (
        verification.status
        is PortalVerificationStatus.CONFIRMED
    )

    assert components[
        component_name
    ].calls == [
        expected_operation
    ]


def test_should_reject_mismatched_verification_step() -> None:
    portal, components = create_portal()
    contract = build_contract()

    components[
        "assistant"
    ].verification_overrides[
        "verify_open"
    ] = ContractStep.HEADER_COMPLETED

    with pytest.raises(
        PortalVerificationMismatchError,
        match="verificación inconsistente",
    ):
        portal.verify_step(
            ContractStep.ASSISTANT_OPENED,
            contract,
        )


def test_should_reject_unsupported_execution_step() -> None:
    portal, _ = create_portal()
    contract = build_contract()

    with pytest.raises(
        UnsupportedPortalStepError,
        match="INPUT_VALIDATED",
    ):
        portal.execute_step(
            ContractStep.INPUT_VALIDATED,
            contract,
        )


def test_should_reject_unsupported_verification_step() -> None:
    portal, _ = create_portal()
    contract = build_contract()

    with pytest.raises(
        UnsupportedPortalStepError,
        match="COMPLETED",
    ):
        portal.verify_step(
            ContractStep.COMPLETED,
            contract,
        )


def test_should_delegate_recovery() -> None:
    portal, components = create_portal()

    portal.recover()

    assert components[
        "recovery"
    ].calls == [
        "recover"
=======
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import pytest

from adapters.portal.gestion_transparente import (
    GestionTransparentePortal,
    PortalVerificationMismatchError,
    UnsupportedPortalStepError,
)
from application.dto import (
    PortalStepVerification,
    PortalVerificationStatus,
)
from domain.enums import (
    ContractStep,
    ContractorNature,
)
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


@dataclass
class RecordingComponent:
    """
    Componente simulado que implementa todos los contratos necesarios.

    Cada dependencia recibe una instancia diferente, permitiendo
    comprobar a cuál componente fue despachada la etapa.
    """

    name: str
    calls: list[str] = field(default_factory=list)

    verification_overrides: dict[
        str,
        ContractStep,
    ] = field(default_factory=dict)

    def _record(
        self,
        operation: str,
    ) -> None:
        self.calls.append(operation)

    def _verification(
        self,
        operation: str,
        expected_step: ContractStep,
    ) -> PortalStepVerification:
        self._record(operation)

        returned_step = self.verification_overrides.get(
            operation,
            expected_step,
        )

        return PortalStepVerification(
            step=returned_step,
            status=PortalVerificationStatus.CONFIRMED,
            message=f"{operation} confirmado",
            metadata={
                "component": self.name,
            },
        )

    # Asistente

    def open(
        self,
        contract: ContractData,
    ) -> None:
        self._record("open")

    def verify_open(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_open",
            ContractStep.ASSISTANT_OPENED,
        )

    # Cabecera

    def complete_header(
        self,
        contract: ContractData,
    ) -> None:
        self._record("complete_header")

    def verify_header_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_header_completed",
            ContractStep.HEADER_COMPLETED,
        )

    def validate_header(
        self,
        contract: ContractData,
    ) -> None:
        self._record("validate_header")

    def verify_header_validated(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_header_validated",
            ContractStep.HEADER_VALIDATED,
        )

    # Datos generales

    def complete_general_data(
        self,
        contract: ContractData,
    ) -> None:
        self._record("complete_general_data")

    def verify_general_data_completed(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_general_data_completed",
            ContractStep.GENERAL_DATA_COMPLETED,
        )

    def save_contract(
        self,
        contract: ContractData,
    ) -> None:
        self._record("save_contract")

    def verify_contract_saved(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_contract_saved",
            ContractStep.CONTRACT_SAVED,
        )

    # Supervisor

    def link_supervisor(
        self,
        contract: ContractData,
    ) -> None:
        self._record("link_supervisor")

    def verify_supervisor_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_supervisor_linked",
            ContractStep.SUPERVISOR_LINKED,
        )

    # Disponibilidad

    def link_availability(
        self,
        contract: ContractData,
    ) -> None:
        self._record("link_availability")

    def verify_availability_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_availability_linked",
            ContractStep.AVAILABILITY_LINKED,
        )

    # Registro presupuestal

    def link_budget_register(
        self,
        contract: ContractData,
    ) -> None:
        self._record("link_budget_register")

    def verify_budget_register_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_budget_register_linked",
            ContractStep.BUDGET_REGISTER_LINKED,
        )

    # Fechas adicionales

    def link_additional_dates(
        self,
        contract: ContractData,
    ) -> None:
        self._record("link_additional_dates")

    def verify_additional_dates_linked(
        self,
        contract: ContractData,
    ) -> PortalStepVerification:
        return self._verification(
            "verify_additional_dates_linked",
            ContractStep.ADDITIONAL_DATES_LINKED,
        )

    # Recuperación

    def recover(self) -> None:
        self._record("recover")


def build_contract() -> ContractData:
    contractor = ContractorData(
        document_number="900469775-8",
        nature=ContractorNature.LEGAL_ENTITY,
    )

    supervisor = SupervisorData(
        document_number="71693738",
        supervisor_type="Supervisor",
    )

    budget = BudgetData(
        year=2026,
        item="IDEA-2026",
        subsector="Tecnología",
        cdp_code="235097",
        gross_total=Decimal("1476190"),
    )

    return ContractData(
        contract_number="70-2026",
        dependency="Proyectos Especiales",
        contractor=contractor,
        project_code="I-23021-2026",
        object_description="Servicio institucional.",
        signing_date=date(2026, 1, 20),
        starting_date=date(2026, 1, 21),
        amount=Decimal("1476190"),
        term_days=180,
        process_type="Contratación Directa",
        procedure="Prestación de Servicios",
        contract_type="Servicios",
        budget=budget,
        supervisor=supervisor,
    )


def create_portal():
    components = {
        "assistant": RecordingComponent(
            "assistant"
        ),
        "header": RecordingComponent(
            "header"
        ),
        "general_data": RecordingComponent(
            "general_data"
        ),
        "supervisor": RecordingComponent(
            "supervisor"
        ),
        "availability": RecordingComponent(
            "availability"
        ),
        "budget_register": RecordingComponent(
            "budget_register"
        ),
        "additional_dates": RecordingComponent(
            "additional_dates"
        ),
        "recovery": RecordingComponent(
            "recovery"
        ),
    }

    portal = GestionTransparentePortal(
        assistant=components["assistant"],
        header=components["header"],
        general_data=components["general_data"],
        supervisor=components["supervisor"],
        availability=components["availability"],
        budget_register=components["budget_register"],
        additional_dates=components[
            "additional_dates"
        ],
        recovery=components["recovery"],
    )

    return portal, components


EXECUTION_CASES = (
    (
        ContractStep.ASSISTANT_OPENED,
        "assistant",
        "open",
    ),
    (
        ContractStep.HEADER_COMPLETED,
        "header",
        "complete_header",
    ),
    (
        ContractStep.HEADER_VALIDATED,
        "header",
        "validate_header",
    ),
    (
        ContractStep.GENERAL_DATA_COMPLETED,
        "general_data",
        "complete_general_data",
    ),
    (
        ContractStep.CONTRACT_SAVED,
        "general_data",
        "save_contract",
    ),
    (
        ContractStep.SUPERVISOR_LINKED,
        "supervisor",
        "link_supervisor",
    ),
    (
        ContractStep.AVAILABILITY_LINKED,
        "availability",
        "link_availability",
    ),
    (
        ContractStep.BUDGET_REGISTER_LINKED,
        "budget_register",
        "link_budget_register",
    ),
    (
        ContractStep.ADDITIONAL_DATES_LINKED,
        "additional_dates",
        "link_additional_dates",
    ),
)


VERIFICATION_CASES = (
    (
        ContractStep.ASSISTANT_OPENED,
        "assistant",
        "verify_open",
    ),
    (
        ContractStep.HEADER_COMPLETED,
        "header",
        "verify_header_completed",
    ),
    (
        ContractStep.HEADER_VALIDATED,
        "header",
        "verify_header_validated",
    ),
    (
        ContractStep.GENERAL_DATA_COMPLETED,
        "general_data",
        "verify_general_data_completed",
    ),
    (
        ContractStep.CONTRACT_SAVED,
        "general_data",
        "verify_contract_saved",
    ),
    (
        ContractStep.SUPERVISOR_LINKED,
        "supervisor",
        "verify_supervisor_linked",
    ),
    (
        ContractStep.AVAILABILITY_LINKED,
        "availability",
        "verify_availability_linked",
    ),
    (
        ContractStep.BUDGET_REGISTER_LINKED,
        "budget_register",
        "verify_budget_register_linked",
    ),
    (
        ContractStep.ADDITIONAL_DATES_LINKED,
        "additional_dates",
        "verify_additional_dates_linked",
    ),
)


@pytest.mark.parametrize(
    (
        "step",
        "component_name",
        "expected_operation",
    ),
    EXECUTION_CASES,
)
def test_should_dispatch_execution_to_expected_component(
    step: ContractStep,
    component_name: str,
    expected_operation: str,
) -> None:
    portal, components = create_portal()
    contract = build_contract()

    portal.execute_step(
        step,
        contract,
    )

    assert components[
        component_name
    ].calls == [
        expected_operation
    ]

    for name, component in components.items():
        if name in {
            component_name,
        }:
            continue

        assert component.calls == []


@pytest.mark.parametrize(
    (
        "step",
        "component_name",
        "expected_operation",
    ),
    VERIFICATION_CASES,
)
def test_should_dispatch_verification_to_expected_component(
    step: ContractStep,
    component_name: str,
    expected_operation: str,
) -> None:
    portal, components = create_portal()
    contract = build_contract()

    verification = portal.verify_step(
        step,
        contract,
    )

    assert verification.step is step
    assert (
        verification.status
        is PortalVerificationStatus.CONFIRMED
    )

    assert components[
        component_name
    ].calls == [
        expected_operation
    ]


def test_should_reject_mismatched_verification_step() -> None:
    portal, components = create_portal()
    contract = build_contract()

    components[
        "assistant"
    ].verification_overrides[
        "verify_open"
    ] = ContractStep.HEADER_COMPLETED

    with pytest.raises(
        PortalVerificationMismatchError,
        match="verificación inconsistente",
    ):
        portal.verify_step(
            ContractStep.ASSISTANT_OPENED,
            contract,
        )


def test_should_reject_unsupported_execution_step() -> None:
    portal, _ = create_portal()
    contract = build_contract()

    with pytest.raises(
        UnsupportedPortalStepError,
        match="INPUT_VALIDATED",
    ):
        portal.execute_step(
            ContractStep.INPUT_VALIDATED,
            contract,
        )


def test_should_reject_unsupported_verification_step() -> None:
    portal, _ = create_portal()
    contract = build_contract()

    with pytest.raises(
        UnsupportedPortalStepError,
        match="COMPLETED",
    ):
        portal.verify_step(
            ContractStep.COMPLETED,
            contract,
        )


def test_should_delegate_recovery() -> None:
    portal, components = create_portal()

    portal.recover()

    assert components[
        "recovery"
    ].calls == [
        "recover"
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
    ]