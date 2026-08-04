from __future__ import annotations

from selenium.common.exceptions import TimeoutException
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
        visible: bool = True,
        enabled: bool = True,
        on_click=None,
    ) -> None:
        self.text = text
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
        return None

    def click(self) -> None:
        self.clicks += 1
        if self.on_click is not None:
            self.on_click()


class FakeControl:
    def __init__(
        self,
        *,
        tag_name: str = "input",
        value: str = "",
        text: str = "",
    ) -> None:
        self.tag_name = tag_name
        self.value = value
        self.text = text
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
        return None

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


class FakeDriver:
    def __init__(self, options: list[FakeOption]) -> None:
        self.options = options

    def find_elements(self, by, value):
        assert value == "[role='listbox'] [role='option']"
        return self.options


class FakeWaits:
    def until(self, condition, **kwargs):
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
