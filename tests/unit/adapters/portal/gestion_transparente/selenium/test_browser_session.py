<<<<<<< HEAD
from __future__ import annotations

import pytest

from adapters.portal.gestion_transparente.selenium.browser_session import (
    BrowserSession,
    BrowserSessionNotStartedError,
)


class FakeDriver:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.refresh_calls = 0
        self.maximize_calls = 0
        self.quit_calls = 0

    def get(self, url: str) -> None:
        self.urls.append(url)

    def refresh(self) -> None:
        self.refresh_calls += 1

    def maximize_window(self) -> None:
        self.maximize_calls += 1

    def quit(self) -> None:
        self.quit_calls += 1


class FakeFactory:
    def __init__(self) -> None:
        self.driver = FakeDriver()
        self.create_calls = 0

    def create(self):
        self.create_calls += 1
        return self.driver


def test_should_require_started_session() -> None:
    session = BrowserSession(
        FakeFactory()
    )

    with pytest.raises(
        BrowserSessionNotStartedError,
        match="no ha sido iniciada",
    ):
        _ = session.driver


def test_should_open_session_idempotently() -> None:
    factory = FakeFactory()
    session = BrowserSession(factory)

    first = session.open()
    second = session.open()

    assert first is second
    assert factory.create_calls == 1
    assert session.is_open


def test_should_manage_context_and_close_driver() -> None:
    factory = FakeFactory()

    with BrowserSession(factory) as session:
        assert session.is_open
        assert session.driver is factory.driver

    assert not session.is_open
    assert factory.driver.quit_calls == 1


def test_should_delegate_browser_operations() -> None:
    factory = FakeFactory()
    session = BrowserSession(factory)

    session.open()
    session.navigate(
        "https://example.test/portal"
    )
    session.refresh()
    session.maximize()

    assert factory.driver.urls == [
        "https://example.test/portal"
    ]
    assert factory.driver.refresh_calls == 1
=======
from __future__ import annotations

import pytest

from adapters.portal.gestion_transparente.selenium.browser_session import (
    BrowserSession,
    BrowserSessionNotStartedError,
)


class FakeDriver:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.refresh_calls = 0
        self.maximize_calls = 0
        self.quit_calls = 0

    def get(self, url: str) -> None:
        self.urls.append(url)

    def refresh(self) -> None:
        self.refresh_calls += 1

    def maximize_window(self) -> None:
        self.maximize_calls += 1

    def quit(self) -> None:
        self.quit_calls += 1


class FakeFactory:
    def __init__(self) -> None:
        self.driver = FakeDriver()
        self.create_calls = 0

    def create(self):
        self.create_calls += 1
        return self.driver


def test_should_require_started_session() -> None:
    session = BrowserSession(
        FakeFactory()
    )

    with pytest.raises(
        BrowserSessionNotStartedError,
        match="no ha sido iniciada",
    ):
        _ = session.driver


def test_should_open_session_idempotently() -> None:
    factory = FakeFactory()
    session = BrowserSession(factory)

    first = session.open()
    second = session.open()

    assert first is second
    assert factory.create_calls == 1
    assert session.is_open


def test_should_manage_context_and_close_driver() -> None:
    factory = FakeFactory()

    with BrowserSession(factory) as session:
        assert session.is_open
        assert session.driver is factory.driver

    assert not session.is_open
    assert factory.driver.quit_calls == 1


def test_should_delegate_browser_operations() -> None:
    factory = FakeFactory()
    session = BrowserSession(factory)

    session.open()
    session.navigate(
        "https://example.test/portal"
    )
    session.refresh()
    session.maximize()

    assert factory.driver.urls == [
        "https://example.test/portal"
    ]
    assert factory.driver.refresh_calls == 1
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
    assert factory.driver.maximize_calls == 1