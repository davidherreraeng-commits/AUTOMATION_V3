<<<<<<< HEAD
from __future__ import annotations

from pathlib import Path

import pytest

from adapters.portal.gestion_transparente.selenium.driver_factory import (
    BrowserSettings,
    BrowserStartupError,
    DriverFactory,
)


class FakeDriver:
    def __init__(self) -> None:
        self.page_load_timeout = None
        self.script_timeout = None
        self.implicit_wait = None
        self.quit_calls = 0

    def set_page_load_timeout(
        self,
        value,
    ) -> None:
        self.page_load_timeout = value

    def set_script_timeout(
        self,
        value,
    ) -> None:
        self.script_timeout = value

    def implicitly_wait(
        self,
        value,
    ) -> None:
        self.implicit_wait = value

    def quit(self) -> None:
        self.quit_calls += 1


def test_should_use_selenium_manager_without_driver_path(
    monkeypatch,
) -> None:
    captured = {}
    driver = FakeDriver()

    def fake_chrome(**kwargs):
        captured.update(kwargs)
        return driver

    monkeypatch.setattr(
        "adapters.portal.gestion_transparente."
        "selenium.driver_factory.webdriver.Chrome",
        fake_chrome,
    )

    created = DriverFactory().create()

    assert created is driver
    assert "options" in captured
    assert "service" not in captured
    assert driver.implicit_wait == 0


def test_should_use_explicit_driver_service(
    tmp_path: Path,
    monkeypatch,
) -> None:
    driver_path = tmp_path / "chromedriver.exe"
    driver_path.write_bytes(b"fake")

    captured = {}
    driver = FakeDriver()

    def fake_chrome(**kwargs):
        captured.update(kwargs)
        return driver

    monkeypatch.setattr(
        "adapters.portal.gestion_transparente."
        "selenium.driver_factory.webdriver.Chrome",
        fake_chrome,
    )

    settings = BrowserSettings(
        driver_path=driver_path
    )

    DriverFactory(settings).create()

    assert "service" in captured
    assert "options" in captured


def test_should_configure_headless_and_downloads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured = {}
    driver = FakeDriver()

    def fake_chrome(**kwargs):
        captured.update(kwargs)
        return driver

    monkeypatch.setattr(
        "adapters.portal.gestion_transparente."
        "selenium.driver_factory.webdriver.Chrome",
        fake_chrome,
    )

    download_directory = tmp_path / "downloads"

    settings = BrowserSettings(
        headless=True,
        download_directory=download_directory,
        additional_arguments=(
            "--lang=es-CO",
        ),
    )

    DriverFactory(settings).create()

    options = captured["options"]

    assert "--headless=new" in options.arguments
    assert "--lang=es-CO" in options.arguments

    preferences = options.experimental_options[
        "prefs"
    ]

    assert preferences[
        "download.default_directory"
    ] == str(download_directory.resolve())


def test_should_reject_unknown_driver_file(
    tmp_path: Path,
) -> None:
    settings = BrowserSettings(
        driver_path=(
            tmp_path / "missing-chromedriver.exe"
        )
    )

    with pytest.raises(
        BrowserStartupError,
        match="No existe",
    ):
=======
from __future__ import annotations

from pathlib import Path

import pytest

from adapters.portal.gestion_transparente.selenium.driver_factory import (
    BrowserSettings,
    BrowserStartupError,
    DriverFactory,
)


class FakeDriver:
    def __init__(self) -> None:
        self.page_load_timeout = None
        self.script_timeout = None
        self.implicit_wait = None
        self.quit_calls = 0

    def set_page_load_timeout(
        self,
        value,
    ) -> None:
        self.page_load_timeout = value

    def set_script_timeout(
        self,
        value,
    ) -> None:
        self.script_timeout = value

    def implicitly_wait(
        self,
        value,
    ) -> None:
        self.implicit_wait = value

    def quit(self) -> None:
        self.quit_calls += 1


def test_should_use_selenium_manager_without_driver_path(
    monkeypatch,
) -> None:
    captured = {}
    driver = FakeDriver()

    def fake_chrome(**kwargs):
        captured.update(kwargs)
        return driver

    monkeypatch.setattr(
        "adapters.portal.gestion_transparente."
        "selenium.driver_factory.webdriver.Chrome",
        fake_chrome,
    )

    created = DriverFactory().create()

    assert created is driver
    assert "options" in captured
    assert "service" not in captured
    assert driver.implicit_wait == 0


def test_should_use_explicit_driver_service(
    tmp_path: Path,
    monkeypatch,
) -> None:
    driver_path = tmp_path / "chromedriver.exe"
    driver_path.write_bytes(b"fake")

    captured = {}
    driver = FakeDriver()

    def fake_chrome(**kwargs):
        captured.update(kwargs)
        return driver

    monkeypatch.setattr(
        "adapters.portal.gestion_transparente."
        "selenium.driver_factory.webdriver.Chrome",
        fake_chrome,
    )

    settings = BrowserSettings(
        driver_path=driver_path
    )

    DriverFactory(settings).create()

    assert "service" in captured
    assert "options" in captured


def test_should_configure_headless_and_downloads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured = {}
    driver = FakeDriver()

    def fake_chrome(**kwargs):
        captured.update(kwargs)
        return driver

    monkeypatch.setattr(
        "adapters.portal.gestion_transparente."
        "selenium.driver_factory.webdriver.Chrome",
        fake_chrome,
    )

    download_directory = tmp_path / "downloads"

    settings = BrowserSettings(
        headless=True,
        download_directory=download_directory,
        additional_arguments=(
            "--lang=es-CO",
        ),
    )

    DriverFactory(settings).create()

    options = captured["options"]

    assert "--headless=new" in options.arguments
    assert "--lang=es-CO" in options.arguments

    preferences = options.experimental_options[
        "prefs"
    ]

    assert preferences[
        "download.default_directory"
    ] == str(download_directory.resolve())


def test_should_reject_unknown_driver_file(
    tmp_path: Path,
) -> None:
    settings = BrowserSettings(
        driver_path=(
            tmp_path / "missing-chromedriver.exe"
        )
    )

    with pytest.raises(
        BrowserStartupError,
        match="No existe",
    ):
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        DriverFactory(settings).create()