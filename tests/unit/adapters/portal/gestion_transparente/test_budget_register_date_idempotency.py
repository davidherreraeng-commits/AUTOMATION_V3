from __future__ import annotations

from adapters.portal.gestion_transparente.batch_portal_probe import (
    SeleniumBatchPortalProbe,
)


def subject() -> SeleniumBatchPortalProbe:
    return object.__new__(SeleniumBatchPortalProbe)


def test_date_match_accepts_single_iso_date() -> None:
    assert subject()._date_field_matches(
        actual="2026-08-03",
        expected="2026-08-03",
    )


def test_date_match_accepts_same_date_with_separators() -> None:
    assert subject()._date_field_matches(
        actual="03/08/2026",
        expected="2026-08-03",
    )
    assert subject()._date_field_matches(
        actual="03-08-2026",
        expected="2026-08-03",
    )


def test_date_match_rejects_concatenated_retries() -> None:
    assert not subject()._date_field_matches(
        actual="2026-08-032026-08-032026-08-03",
        expected="2026-08-03",
    )
