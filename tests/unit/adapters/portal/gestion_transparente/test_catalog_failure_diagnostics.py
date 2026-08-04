from __future__ import annotations

import json
from pathlib import Path

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)


class FakeElement:
    tag_name = "input"
    text = ""

    def __init__(self, attributes: dict[str, object]) -> None:
        self.attributes = attributes

    def get_attribute(self, name: str):
        return self.attributes.get(name)


class FakeOption(FakeElement):
    text = "01 - Tecnología"

    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True


class FakeResolver:
    def __init__(self, element: FakeElement) -> None:
        self.element = element

    def visible(self, key: str, timeout_seconds: float):
        return self.element


class FakeDriver:
    current_url = "https://portal.test/contract"
    page_source = "<html><body>catalog</body></html>"

    def find_elements(self, by, value):
        return [
            FakeOption(
                {
                    "aria-selected": "false",
                    "id": "option-1",
                    "outerHTML": "<li role='option'>01 - Tecnología</li>",
                }
            )
        ]

    def execute_script(self, script: str, element: FakeElement):
        if ".closest(" in script:
            return "<div class='MuiAutocomplete-root'></div>"
        return element.get_attribute("value")

    def save_screenshot(self, filename: str) -> bool:
        Path(filename).write_bytes(b"png")
        return True


def subject() -> SeleniumBatchPortalProbe:
    instance = object.__new__(SeleniumBatchPortalProbe)
    instance._timeout_seconds = 1.0
    return instance


def test_should_capture_catalog_failure_state(tmp_path: Path) -> None:
    element = FakeElement(
        {
            "id": "budgetItem",
            "value": "",
            "textContent": "",
            "outerHTML": "<input id='budgetItem' value=''>",
            "class": "MuiAutocomplete-input",
            "role": "combobox",
            "aria-expanded": "true",
        }
    )

    evidence = subject()._capture_catalog_failure_evidence(
        driver=FakeDriver(),
        resolver=FakeResolver(element),
        key="general.budget_item",
        expected="IDEA-2026",
        code="GENERAL_BUDGET_ITEM_SELECTION_FAILED",
        label="Rubro Presupuestal",
        attempts=["intento 1: valor confirmado=''"],
        output_root=tmp_path,
    )

    assert evidence is not None
    directory = Path(evidence)
    assert (directory / "catalog_state.json").is_file()
    assert (directory / "page_source.html").is_file()
    assert (directory / "screenshot.png").is_file()

    state = json.loads(
        (directory / "catalog_state.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["key"] == "general.budget_item"
    assert state["control"]["id"] == "budgetItem"
    assert state["control"]["dom_value_property"] == ""
    assert state["visible_options"][0]["text"] == "01 - Tecnología"


def test_should_return_none_when_evidence_directory_cannot_be_created(
    tmp_path: Path,
) -> None:
    occupied = tmp_path / "occupied"
    occupied.write_text("not a directory", encoding="utf-8")

    element = FakeElement({"value": ""})
    result = subject()._capture_catalog_failure_evidence(
        driver=FakeDriver(),
        resolver=FakeResolver(element),
        key="general.budget_item",
        expected="IDEA-2026",
        code="ERROR",
        label="Rubro",
        attempts=[],
        output_root=occupied,
    )

    assert result is None
