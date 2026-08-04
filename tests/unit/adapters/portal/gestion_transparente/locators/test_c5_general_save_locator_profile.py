from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_scope_final_validation_to_general_form() -> None:
    candidate = build_registry().candidates(
        "general.final_validate_button"
    )[0]

    assert "executionCity" in candidate.value
    assert "Validar" in candidate.value


def test_should_use_save_as_validation_postcondition() -> None:
    registry = build_registry()

    validation = registry.candidates(
        "general.validation_success"
    )[0]

    save_button = registry.candidates(
        "general.save_button"
    )[0]

    assert "executionCity" in validation.value
    assert "Guardar" in validation.value
    assert validation.value == save_button.value


def test_should_scope_accept_to_success_dialog() -> None:
    registry = build_registry()

    dialog = registry.candidates(
        "general.save_success_dialog"
    )[0].value

    accept = registry.candidates(
        "general.save_success_accept"
    )[0].value

    assert "Éxito" in dialog
    assert (
        "Se ha registrado el contrato exitosamente"
        in dialog
    )

    assert "@role='dialog'" in accept
    assert "Aceptar" in accept


def test_should_verify_saved_contract_on_next_stage() -> None:
    candidates = build_registry().candidates(
        "general.contract_saved"
    )

    assert (
        candidates[0].value
        == "input[name='CONTRACT_IDENTIFIER']"
    )

    assert (
        candidates[1].value
        == "input[name='CONTRACTOR_IDENTIFIER']"
    )


def test_should_register_supervisor_section() -> None:
    candidates = build_registry().candidates(
        "supervisor.section"
    )

    assert (
        "VINCULAR INTERVENTOR/SUPERVISOR"
        in candidates[0].value
    )

    assert (
        candidates[1].value
        == (
            "button[title="
            "'Buscar Interventor / Supervisor']"
        )
    )