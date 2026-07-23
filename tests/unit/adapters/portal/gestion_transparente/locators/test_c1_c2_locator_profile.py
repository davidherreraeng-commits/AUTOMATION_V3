from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_register_complete_navigation_path() -> None:
    registry = build_registry()

    assert registry.candidates(
        "navigation.contracting_menu"
    )

    assert registry.candidates(
        "navigation.enter_contract"
    )

    assert registry.candidates(
        "assistant.open"
    )


def test_should_register_contract_record_type() -> None:
    candidates = build_registry().candidates(
        "contract.header.record_type_contract"
    )

    assert candidates[0].by == By.CSS_SELECTOR

    assert (
        candidates[0].value
        == "input[name='contractType'][value='1']"
    )


def test_should_separate_contractor_natures() -> None:
    registry = build_registry()

    legal = registry.candidates(
        "contractor.legal.document_input"
    )

    natural = registry.candidates(
        "contractor.natural.document_input"
    )

    assert "corpIdNumber" in legal[0].value
    assert "idNumber" in natural[0].value

    assert (
        legal[0].value
        != natural[0].value
    )


def test_should_register_project_dialog_flow() -> None:
    registry = build_registry()

    assert registry.candidates(
        "project.dialog"
    )

    assert (
        registry.candidates(
            "project.code_input"
        )[0].value
        == (
            "[role='dialog'] "
            "input[name='projectId']"
        )
    )

    assert registry.candidates(
        "project.result_row"
    )

    assert registry.candidates(
        "project.confirm_button"
    )