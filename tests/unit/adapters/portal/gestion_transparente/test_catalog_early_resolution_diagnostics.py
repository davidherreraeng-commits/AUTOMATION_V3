from __future__ import annotations

from typing import Any

import pytest

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)
from domain.errors import PortalTimeoutError


class FailingResolver:
    def clickable(self, key: str, timeout_seconds: float):
        raise PortalTimeoutError(
            f"No fue posible resolver {key}.",
            code="PORTAL_TIMEOUT",
            metadata={"key": key},
        )


class FakeDriver:
    pass


def subject() -> SeleniumBatchPortalProbe:
    instance = object.__new__(SeleniumBatchPortalProbe)
    instance._timeout_seconds = 1.0
    return instance


def test_should_capture_when_resolver_fails_before_catalog_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_capture(**kwargs):
        captured.update(kwargs)
        return r"D:\automation_v2\artifacts\diagnostics\catalogs\evidence"

    instance = subject()
    monkeypatch.setattr(
        instance,
        "_capture_catalog_failure_evidence",
        fake_capture,
    )
    attempts: list[str] = []

    with pytest.raises(PortalTimeoutError) as raised:
        instance._resolve_catalog_clickable_or_capture(
            driver=FakeDriver(),
            resolver=FailingResolver(),
            key="general.budget_item",
            expected="IDEA-2026",
            code="GENERAL_BUDGET_ITEM_SELECTION_FAILED",
            label="Rubro Presupuestal",
            attempts=attempts,
        )

    assert raised.value.code == "GENERAL_BUDGET_ITEM_SELECTION_FAILED"
    assert captured["key"] == "general.budget_item"
    assert captured["expected"] == "IDEA-2026"
    assert captured["attempts"] == attempts
    assert attempts
    assert "PORTAL_TIMEOUT" in attempts[0]


def test_should_include_evidence_path_in_wrapped_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = (
        r"D:\automation_v2\artifacts\diagnostics\catalogs"
        r"\20260803_general.budget_item"
    )
    instance = subject()
    monkeypatch.setattr(
        instance,
        "_capture_catalog_failure_evidence",
        lambda **_: evidence,
    )

    with pytest.raises(PortalTimeoutError) as raised:
        instance._resolve_catalog_clickable_or_capture(
            driver=FakeDriver(),
            resolver=FailingResolver(),
            key="general.budget_item",
            expected="IDEA-2026",
            code="GENERAL_BUDGET_ITEM_SELECTION_FAILED",
            label="Rubro Presupuestal",
            attempts=[],
        )

    assert raised.value.metadata["evidence_directory"] == evidence
    assert raised.value.metadata["resolver_error_code"] == "PORTAL_TIMEOUT"
