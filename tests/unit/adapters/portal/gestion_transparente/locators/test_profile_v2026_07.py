from __future__ import annotations

import pytest

from adapters.portal.gestion_transparente.locators import (
    DuplicateLocatorError,
    LocatorSpec,
)
from adapters.portal.gestion_transparente.locators.profiles import (
    PortalLocatorProfile,
    ProfileValidationError,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    PROFILE_VERSION,
    REQUIRED_LOCATOR_KEYS,
    build_profile,
    build_registry,
)


def test_should_build_complete_versioned_profile() -> None:
    profile = build_profile()

    assert profile.version == PROFILE_VERSION
    assert profile.version == "v2026_07"

    assert REQUIRED_LOCATOR_KEYS <= profile.keys


def test_should_build_independent_registries() -> None:
    first = build_registry()
    second = build_registry()

    assert first is not second

    assert (
        first.keys()
        == second.keys()
    )

    assert (
        first.candidates(
            "portal.login.username"
        )
        == second.candidates(
            "portal.login.username"
        )
    )


def test_should_reject_missing_required_key() -> None:
    locator = LocatorSpec(
        key="existing.key",
        by="id",
        value="existing",
    )

    with pytest.raises(
        ProfileValidationError,
        match="missing.key",
    ):
        PortalLocatorProfile(
            version="test",
            locators=(locator,),
            required_keys=frozenset(
                {
                    "existing.key",
                    "missing.key",
                }
            ),
        )


def test_should_reject_duplicate_locator() -> None:
    locator = LocatorSpec(
        key="duplicate.key",
        by="id",
        value="same-value",
    )

    with pytest.raises(
        DuplicateLocatorError,
        match="ya se encuentra registrado",
    ):
        PortalLocatorProfile(
            version="test",
            locators=(
                locator,
                locator,
            ),
        )