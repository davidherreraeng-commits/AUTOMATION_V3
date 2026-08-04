from __future__ import annotations

import pytest

from adapters.portal.gestion_transparente.selenium.browser_session import (
    BrowserSession,
    BrowserSessionError,
)


class FakeDriver:
    def __init__(self, *, quit_error: Exception | None = None) -> None:
        self.quit_error = quit_error
        self.quit_calls = 0

    def quit(self) -> None:
        self.quit_calls += 1
        if self.quit_error is not None:
            raise self.quit_error


class FakeFactory:
    def __init__(self, driver: FakeDriver) -> None:
        self.driver = driver
        self.create_calls = 0

    def create(self):
        self.create_calls += 1
        return self.driver


def test_context_manager_should_reuse_and_close_single_driver() -> None:
    driver = FakeDriver()
    session = BrowserSession(FakeFactory(driver))

    with session as opened:
        assert opened.driver is driver
        assert opened.open() is driver

    assert driver.quit_calls == 1
    assert session.is_open is False


def test_close_error_should_not_mask_original_exception() -> None:
    driver = FakeDriver(quit_error=RuntimeError("quit failed"))
    session = BrowserSession(FakeFactory(driver))

    with pytest.raises(ValueError, match="original"):
        with session:
            raise ValueError("original")

    assert driver.quit_calls == 1


def test_close_error_should_surface_without_previous_exception() -> None:
    driver = FakeDriver(quit_error=RuntimeError("quit failed"))
    session = BrowserSession(FakeFactory(driver))

    with pytest.raises(BrowserSessionError):
        with session:
            pass
