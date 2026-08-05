from __future__ import annotations

import pytest
from pydantic import ValidationError

from infrastructure.config.settings import Settings


def test_should_parse_nominal_value_contract_allowlist_from_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "RPA_BATCH_EXECUTION_NOMINAL_VALUE_CONTRACT_ALLOWLIST",
        " 70-2026, contrato   especial,70-2026 ",
    )

    settings = Settings(_env_file=None)

    assert settings.batch_execution_nominal_value_contract_allowlist == [
        "70-2026",
        "CONTRATO ESPECIAL",
    ]


def test_should_reject_wildcard_nominal_value_allowlist(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "RPA_BATCH_EXECUTION_NOMINAL_VALUE_CONTRACT_ALLOWLIST",
        "*",
    )

    with pytest.raises(ValidationError, match="no admite"):
        Settings(_env_file=None)
