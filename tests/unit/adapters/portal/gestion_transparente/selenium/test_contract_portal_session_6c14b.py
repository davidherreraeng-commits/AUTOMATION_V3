from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from adapters.portal.gestion_transparente.selenium.contract_portal_session import (
    _SeleniumContractComponents,
)
from application.dto import PortalVerificationStatus
from domain.enums import ContractStep, ContractorNature
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)


class FakeElement:
    def __init__(self, value: str = "") -> None:
        self.text = value
        self._value = value

    def get_attribute(self, name: str):
        return self._value if name == "value" else None


@dataclass
class FakeResolver:
    visible_keys: set[str] = field(default_factory=set)
    values: dict[str, str] = field(default_factory=dict)

    def optional_visible(self, key: str, *, timeout_seconds: float = 2.0):
        if key not in self.visible_keys:
            return None
        return FakeElement(self.values.get(key, ""))


class FakeDriver:
    def __init__(self) -> None:
        self.refresh_calls = 0

    def refresh(self) -> None:
        self.refresh_calls += 1


class FakeHelper:
    pass


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


def build_components(resolver: FakeResolver):
    driver = FakeDriver()
    components = _SeleniumContractComponents(
        driver=driver,
        waits=object(),
        resolver=resolver,
        helper=FakeHelper(),
        timeout_seconds=10,
    )
    return driver, components


def test_should_confirm_each_stage_from_next_visible_section() -> None:
    cases = (
        ({"assistant.container"}, "verify_open", ContractStep.ASSISTANT_OPENED),
        (
            {"general.object_description"},
            "verify_header_validated",
            ContractStep.HEADER_VALIDATED,
        ),
        (
            {"general.save_button"},
            "verify_general_data_completed",
            ContractStep.GENERAL_DATA_COMPLETED,
        ),
        (
            {"supervisor.section"},
            "verify_contract_saved",
            ContractStep.CONTRACT_SAVED,
        ),
        (
            {"availability.section"},
            "verify_supervisor_linked",
            ContractStep.SUPERVISOR_LINKED,
        ),
        (
            {"budget_register.section"},
            "verify_availability_linked",
            ContractStep.AVAILABILITY_LINKED,
        ),
        (
            {"additional_dates.section"},
            "verify_budget_register_linked",
            ContractStep.BUDGET_REGISTER_LINKED,
        ),
        (
            {"file_reported.section"},
            "verify_additional_dates_linked",
            ContractStep.ADDITIONAL_DATES_LINKED,
        ),
    )
    contract = build_contract()

    for keys, method_name, expected_step in cases:
        _, components = build_components(FakeResolver(set(keys)))
        verification = getattr(components, method_name)(contract)
        assert verification.step is expected_step
        assert verification.status is PortalVerificationStatus.CONFIRMED


def test_header_completed_should_require_expected_contract_number() -> None:
    resolver = FakeResolver(
        visible_keys={
            "contract.header.validate_button",
            "contract.header.contract_number",
        },
        values={"contract.header.contract_number": "70-2026"},
    )
    _, components = build_components(resolver)

    verification = components.verify_header_completed(build_contract())

    assert verification.status is PortalVerificationStatus.CONFIRMED


def test_recover_should_refresh_same_driver() -> None:
    driver, components = build_components(FakeResolver())

    components.recover()

    assert driver.refresh_calls == 1


class FakeEvidence:
    def as_metadata(self) -> dict[str, str]:
        return {"metadata_path": "evidence/metadata.json"}


class FakeDiagnostics:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def capture(self, *, event: str, metadata, error):
        self.calls.append(
            {
                "event": event,
                "metadata": dict(metadata),
                "error": error,
            }
        )
        return FakeEvidence()


def test_failure_capture_should_enrich_portal_error_metadata() -> None:
    from domain.errors import PortalTimeoutError

    diagnostics = FakeDiagnostics()
    error = PortalTimeoutError("No respondió.")

    from adapters.portal.gestion_transparente.selenium.contract_portal_session import (
        SeleniumContractPortalSessionFactory,
    )

    SeleniumContractPortalSessionFactory._capture_failure(
        diagnostics=diagnostics,
        dependency="Proyectos Especiales",
        error=error,
    )

    assert diagnostics.calls[0]["event"] == (
        "controlled_contract_execution_failure"
    )
    assert error.metadata["diagnostics"]["metadata_path"] == (
        "evidence/metadata.json"
    )
