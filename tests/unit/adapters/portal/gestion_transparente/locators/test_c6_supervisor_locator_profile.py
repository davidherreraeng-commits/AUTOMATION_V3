from __future__ import annotations

from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    build_registry,
)


def test_should_register_supervisor_dialog() -> None:
    registry = build_registry()

    assert (
        registry.candidates(
            "supervisor.search_open"
        )[0].value
        == (
            "button[title="
            "'Buscar Interventor / Supervisor']"
        )
    )

    assert (
        "Interventores"
        in registry.candidates(
            "supervisor.dialog"
        )[0].value
    )


def test_should_register_person_nature_and_identity() -> None:
    registry = build_registry()

    nature = registry.candidates(
        "supervisor.nature_person"
    )[0].value

    assert "controlerNature" in nature
    assert "[value='PERSON']" in nature

    assert (
        registry.candidates(
            "supervisor.id_type"
        )[0].value
        == "[role='dialog'] input#idType"
    )

    assert (
        registry.candidates(
            "supervisor.document_input"
        )[0].value
        == (
            "[role='dialog'] "
            "input[name='idNumber']"
        )
    )


def test_should_register_automatic_search_results() -> None:
    registry = build_registry()

    search = registry.candidates(
        "supervisor.search_button"
    )

    assert len(search) == 2
    assert "Interventores" in search[0].value
    assert "BUSCAR" in search[0].value

    assert (
        "[role='row'][data-id]"
        in registry.candidates(
            "supervisor.result_row"
        )[0].value
    )

    assert (
        "button[title='Seleccionar']"
        in registry.candidates(
            "supervisor.select_button"
        )[0].value
    )


def test_should_register_selected_supervisor() -> None:
    candidate = build_registry().candidates(
        "supervisor.selected_identifier"
    )[0]

    assert (
        "Buscar Interventor / Supervisor"
        in candidate.value
    )
    assert "MuiInputBase-root" in candidate.value


def test_should_register_supervisor_type_and_contract() -> None:
    registry = build_registry()

    type_candidate = registry.candidates(
        "supervisor.type_input"
    )[0].value

    assert "controler.0.type" in type_candidate
    assert "@role='combobox'" in type_candidate

    assert (
        registry.candidates(
            "supervisor.contract_input"
        )[0].value
        == "input[name='controler.0.contractId']"
    )


def test_should_register_validation_and_linking() -> None:
    registry = build_registry()

    validate_candidates = registry.candidates(
        "supervisor.validate_button"
    )

    validation_candidates = registry.candidates(
        "supervisor.validation_success"
    )

    link_candidates = registry.candidates(
        "supervisor.link_button"
    )

    assert len(validate_candidates) == 2
    assert len(validation_candidates) == 2
    assert len(link_candidates) == 2

    primary_validate = validate_candidates[0].value
    primary_validation = validation_candidates[0].value
    primary_link = link_candidates[0].value

    assert "controler.0.type" in primary_validate
    assert "MuiCard-root" in primary_validate
    assert "Validar" in primary_validate

    assert "controler.0.type" in primary_validation
    assert "MuiCard-root" in primary_validation
    assert "Vincular" in primary_validation

    assert primary_validation == primary_link

    assert (
        "VINCULAR INTERVENTOR/SUPERVISOR"
        in validate_candidates[1].value
    )
    assert (
        "VINCULAR INTERVENTOR/SUPERVISOR"
        in link_candidates[1].value
    )

def test_should_register_success_and_availability() -> None:
    registry = build_registry()

    dialog = registry.candidates(
        "supervisor.link_success_dialog"
    )[0].value

    accept = registry.candidates(
        "supervisor.link_success_accept"
    )[0].value

    linked = registry.candidates(
        "supervisor.linked"
    )[0].value

    availability = registry.candidates(
        "availability.section"
    )[0].value

    assert (
        "Se ha vinculado el interventor exitosamente"
        in dialog
    )
    assert "Aceptar" in accept
    assert "DISPONIBILIDAD PRESUPUESTAL" in linked
    assert linked == availability