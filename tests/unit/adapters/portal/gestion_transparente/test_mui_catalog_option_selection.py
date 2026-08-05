from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)


class FakeOption:
    tag_name = "li"

    def __init__(
        self,
        text: str,
        *,
        option_id: str = "catalog-option-0",
        visible: bool = True,
        enabled: bool = True,
        on_click=None,
    ) -> None:
        self.text = text
        self.option_id = option_id
        self.visible = visible
        self.enabled = enabled
        self.on_click = on_click
        self.clicks = 0

    def is_displayed(self) -> bool:
        return self.visible

    def is_enabled(self) -> bool:
        return self.enabled

    def get_attribute(self, name: str):
        if name == "textContent":
            return self.text
        if name == "id":
            return self.option_id
        return None

    def click(self) -> None:
        self.clicks += 1
        if self.on_click is not None:
            self.on_click()


class FakeClearButton:
    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True


class FakeAutocompleteRoot:
    def __init__(self, control: "FakeControl") -> None:
        self.control = control

    def get_attribute(self, name: str):
        if name == "class":
            classes = ["MuiAutocomplete-root"]
            if self.control.committed:
                classes.append("MuiAutocomplete-hasClearIcon")
            if self.control.expanded:
                classes.append("Mui-expanded")
            return " ".join(classes)
        return None

    def find_elements(self, by, value):
        if (
            by == By.CSS_SELECTOR
            and value == "button.MuiAutocomplete-clearIndicator"
            and self.control.committed
        ):
            return [FakeClearButton()]
        return []


class FakeControl:
    def __init__(
        self,
        *,
        tag_name: str = "input",
        value: str = "",
        text: str = "",
        aria_controls: str = "catalog-listbox",
        active_descendant: str | None = None,
        committed: bool = False,
        expanded: bool = False,
    ) -> None:
        self.tag_name = tag_name
        self.value = value
        self.text = text
        self.aria_controls = aria_controls
        self.active_descendant = active_descendant
        self.committed = committed
        self.expanded = expanded
        self.clicks = 0
        self.sent: list[object] = []
        self._selected_all = False

    def click(self) -> None:
        self.clicks += 1

    def get_attribute(self, name: str):
        if name == "value":
            return self.value
        if name == "textContent":
            return self.text
        if name == "contenteditable":
            return None
        if name == "aria-controls":
            return self.aria_controls
        if name == "aria-activedescendant":
            return self.active_descendant
        if name == "aria-expanded":
            return "true" if self.expanded else "false"
        if name == "aria-invalid":
            return "false"
        return None

    def find_elements(self, by, value):
        if by == By.XPATH and "MuiAutocomplete-root" in value:
            return [FakeAutocompleteRoot(self)]
        return []

    def send_keys(self, *values) -> None:
        self.sent.extend(values)
        if values == (Keys.CONTROL, "a"):
            self._selected_all = True
            return

        for value in values:
            if value == Keys.BACKSPACE:
                if self._selected_all:
                    self.value = ""
                    self._selected_all = False
                continue
            if value in {
                Keys.ARROW_DOWN,
                Keys.ENTER,
                Keys.TAB,
                Keys.CONTROL,
            }:
                continue
            if self.tag_name in {"input", "textarea"}:
                self.value += str(value)


class FakeListbox:
    def __init__(self, options: list[FakeOption]) -> None:
        self.options = options

    def find_elements(self, by, value):
        assert by == By.CSS_SELECTOR
        assert value == "[role='option']"
        return self.options


class FakeDriver:
    def __init__(
        self,
        options: list[FakeOption],
        *,
        listbox_id: str = "catalog-listbox",
        unrelated_options: list[FakeOption] | None = None,
    ) -> None:
        self.options = options
        self.listbox_id = listbox_id
        self.unrelated_options = unrelated_options or []

    def find_elements(self, by, value):
        if by == By.CSS_SELECTOR:
            assert value == "[role='listbox'] [role='option']"
            return self.unrelated_options + self.options
        if by == By.ID and value == self.listbox_id:
            return [FakeListbox(self.options)]
        if by == By.ID:
            return [
                option
                for option in self.unrelated_options + self.options
                if option.option_id == value
            ]
        raise AssertionError((by, value))


class FakeWaits:
    def until(self, condition, **kwargs):
        for _ in range(12):
            result = condition(kwargs.get("driver") or self.driver)
            if result:
                return result
        raise TimeoutException("condition not met")

    def __init__(self, driver) -> None:
        self.driver = driver


class FakeResolver:
    def __init__(self, control: FakeControl) -> None:
        self.control = control

    def clickable(self, key: str, **kwargs):
        return self.control

    def visible(self, key: str, **kwargs):
        return self.control


def probe() -> SeleniumBatchPortalProbe:
    return SeleniumBatchPortalProbe(
        login_url="https://example.test/login",
        timeout_seconds=20,
        factory=object(),
    )


def configure_clicks(subject: SeleniumBatchPortalProbe) -> None:
    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]
    subject._perform_click = (  # type: ignore[method-assign]
        lambda **kwargs: kwargs["element"].click()
    )


def test_mui_select_clicks_internal_option_and_reads_combobox_text() -> None:
    subject = probe()
    configure_clicks(subject)
    control = FakeControl(tag_name="div")
    option = FakeOption("Interno", on_click=lambda: setattr(control, "text", "Interno"))
    driver = FakeDriver([option])

    subject._select_autocomplete_and_confirm(
        driver=driver,
        waits=FakeWaits(driver),
        resolver=FakeResolver(control),
        key="supervisor.type_input",
        expected="Interno",
        code="SUPERVISOR_TYPE_NOT_INTERNAL",
        label="tipo Interno del supervisor",
    )

    assert option.clicks == 1
    assert subject._resolved_autocomplete_value(
        resolver=FakeResolver(control),
        key="supervisor.type_input",
    ) == "Interno"


def test_subsector_clicks_decorated_option_instead_of_only_using_keyboard() -> None:
    subject = probe()
    configure_clicks(subject)
    control = FakeControl()
    option = FakeOption(
        "01 - Tecnología",
        on_click=lambda: setattr(control, "value", "01 - Tecnología"),
    )
    driver = FakeDriver([option])

    subject._select_autocomplete_and_confirm(
        driver=driver,
        waits=FakeWaits(driver),
        resolver=FakeResolver(control),
        key="general.budget_subsector",
        expected="Tecnología",
        code="GENERAL_BUDGET_SUBSECTOR_SELECTION_FAILED",
        label="Sub-Sector",
        allow_decorated_value=True,
    )

    assert option.clicks == 1
    assert "Tecnología" in control.sent


def test_municipality_accepts_code_and_description_option() -> None:
    subject = probe()
    configure_clicks(subject)
    control = FakeControl()
    option = FakeOption(
        "05001 - Medellín",
        on_click=lambda: setattr(control, "value", "05001 - Medellín"),
    )
    driver = FakeDriver([option])

    subject._select_autocomplete_and_confirm(
        driver=driver,
        waits=FakeWaits(driver),
        resolver=FakeResolver(control),
        key="general.execution_city",
        expected="Medellín",
        code="GENERAL_EXECUTION_CITY_SELECTION_FAILED",
        label="Municipio de Ejecución",
        allow_decorated_value=True,
    )

    assert option.clicks == 1


def test_catalog_option_ignores_hidden_and_unrelated_results() -> None:
    subject = probe()
    configure_clicks(subject)
    hidden = FakeOption("Interno", visible=False)
    unrelated = FakeOption("Externo")
    expected = FakeOption("Interno")
    driver = FakeDriver([hidden, unrelated, expected])

    selected = subject._click_visible_catalog_option(
        driver=driver,
        waits=FakeWaits(driver),
        expected="Interno",
        allow_decorated_value=False,
    )

    assert selected == "Interno"
    assert hidden.clicks == 0
    assert unrelated.clicks == 0
    assert expected.clicks == 1


def test_first_catalog_selection_clicks_first_visible_plan() -> None:
    subject = probe()
    configure_clicks(subject)
    control = FakeControl()
    first = FakeOption(
        "Plan institucional vigente",
        on_click=lambda: setattr(
            control,
            "value",
            "Plan institucional vigente",
        ),
    )
    second = FakeOption("Plan anterior")
    driver = FakeDriver([first, second])

    selected = subject._select_first_autocomplete_and_confirm(
        driver=driver,
        waits=FakeWaits(driver),
        resolver=FakeResolver(control),
        key="general.government_plan",
        code="GENERAL_GOVERNMENT_PLAN_SELECTION_FAILED",
        label="Plan de Gobierno",
    )

    assert selected == "Plan institucional vigente"
    assert first.clicks == 1
    assert second.clicks == 0


def test_option_matching_normalizes_accents_and_decorated_values() -> None:
    subject = probe()

    assert subject._catalog_option_matches(
        actual="05001 - MEDELLIN",
        expected="Medellín",
        allow_decorated_value=True,
    )
    assert subject._catalog_option_matches(
        actual="INTERNO",
        expected="Interno",
        allow_decorated_value=False,
    )

def test_catalog_selection_scopes_options_to_target_listbox() -> None:
    subject = probe()
    configure_clicks(subject)
    control = FakeControl(aria_controls="procedure-listbox")
    target = FakeOption(
        "Contratación Directa - Sin Pluralidad De Oferentes",
        option_id="procedure-option-4",
    )
    unrelated = FakeOption(
        "Sin Pluralidad De Oferentes",
        option_id="type-option-2",
    )
    driver = FakeDriver(
        [target],
        listbox_id="procedure-listbox",
        unrelated_options=[unrelated],
    )

    selected = subject._click_visible_catalog_option(
        driver=driver,
        waits=FakeWaits(driver),
        expected="Sin Pluralidad De Oferentes",
        allow_decorated_value=True,
        control=control,
    )

    assert selected == (
        "Contratación Directa - Sin Pluralidad De Oferentes"
    )
    assert target.clicks == 1
    assert unrelated.clicks == 0


def test_keyboard_fallback_refuses_unmatched_active_option() -> None:
    subject = probe()
    control = FakeControl(
        active_descendant="procedure-option-0",
    )
    active = FakeOption(
        "Arrendamiento y Adquisición de inmuebles",
        option_id="procedure-option-0",
    )
    driver = FakeDriver([active])

    selected = subject._select_catalog_with_keyboard(
        driver=driver,
        resolver=FakeResolver(control),
        key="general.typology",
        expected="Sin Pluralidad De Oferentes",
        allow_decorated_value=True,
        control=control,
    )

    assert selected is False
    assert Keys.ENTER not in control.sent
    assert Keys.TAB not in control.sent


def test_keyboard_fallback_accepts_matching_decorated_option() -> None:
    subject = probe()
    control = FakeControl(
        active_descendant="procedure-option-4",
    )
    active = FakeOption(
        "Contratación Directa - Sin Pluralidad De Oferentes",
        option_id="procedure-option-4",
    )
    driver = FakeDriver([active])

    selected = subject._select_catalog_with_keyboard(
        driver=driver,
        resolver=FakeResolver(control),
        key="general.typology",
        expected="Sin Pluralidad De Oferentes",
        allow_decorated_value=True,
        control=control,
    )

    assert selected is True
    assert Keys.ENTER in control.sent
    assert Keys.TAB in control.sent

def test_catalog_retries_pointer_modes_when_click_does_not_commit() -> None:
    subject = probe()
    control = FakeControl()
    option = FakeOption("Sin Pluralidad de Oferentes")
    driver = FakeDriver([option])
    modes: list[str] = []

    subject._scroll_into_view = lambda *args, **kwargs: None  # type: ignore[method-assign]

    def perform_click(**kwargs) -> None:
        mode = kwargs["mode"]
        modes.append(mode)
        if mode == "actions":
            # Simula un clic que escribe texto, pero no compromete el objeto
            # seleccionado de Material UI.
            control.value = "Sin Pluralidad de Oferentes"
            control.committed = False
        if mode == "native":
            control.value = "Sin Pluralidad de Oferentes"
            control.committed = True

    subject._perform_click = perform_click  # type: ignore[method-assign]

    subject._select_autocomplete_and_confirm(
        driver=driver,
        waits=FakeWaits(driver),
        resolver=FakeResolver(control),
        key="general.typology",
        expected="Sin Pluralidad de Oferentes",
        code="GENERAL_PROCEDURE_SELECTION_FAILED",
        label="Procedimiento o Causal",
        allow_decorated_value=True,
        require_committed_state=True,
    )

    assert modes[:2] == ["actions", "native"]
    assert control.value == "Sin Pluralidad de Oferentes"


def test_stable_confirmation_rejects_transient_input_text() -> None:
    subject = probe()
    control = FakeControl(value="Sin Pluralidad de Oferentes")
    driver = FakeDriver([])
    resolver = FakeResolver(control)
    reads = 0

    original = subject._autocomplete_selection_confirmed

    def transient(**kwargs) -> bool:
        nonlocal reads
        reads += 1
        if reads == 2:
            control.value = ""
        return original(**kwargs)

    subject._autocomplete_selection_confirmed = transient  # type: ignore[method-assign]

    confirmed = subject._wait_for_stable_autocomplete_selection(
        waits=FakeWaits(driver),
        resolver=resolver,
        key="general.typology",
        expected="Sin Pluralidad de Oferentes",
        allow_decorated_value=True,
        alternative_clickable_key=None,
        timeout_seconds=2.0,
        required_polls=3,
        raise_on_timeout=False,
    )

    assert confirmed is False
    assert control.value == ""

def test_typology_requires_material_ui_committed_state() -> None:
    subject = probe()
    control = FakeControl(
        value="Sin Pluralidad de Oferentes",
        committed=False,
    )
    resolver = FakeResolver(control)

    assert subject._autocomplete_selection_confirmed(
        resolver=resolver,
        key="general.typology",
        expected="Sin Pluralidad de Oferentes",
        allow_decorated_value=True,
        alternative_clickable_key=None,
        require_committed_state=True,
    ) is False

    control.committed = True

    assert subject._autocomplete_selection_confirmed(
        resolver=resolver,
        key="general.typology",
        expected="Sin Pluralidad de Oferentes",
        allow_decorated_value=True,
        alternative_clickable_key=None,
        require_committed_state=True,
    ) is True


def test_committed_state_rejects_open_popup() -> None:
    subject = probe()
    control = FakeControl(
        value="Sin Pluralidad de Oferentes",
        committed=True,
        expanded=True,
    )

    assert subject._mui_autocomplete_selection_is_committed(
        resolver=FakeResolver(control),
        key="general.typology",
    ) is False
