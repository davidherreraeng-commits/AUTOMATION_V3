from __future__ import annotations

from datetime import datetime
from typing import Protocol

from domain.models.portal_credentials import PortalCredentials


class PortalCredentialRepository(Protocol):
    """Persistencia de credenciales de portal por dependencia."""

    def find_by_dependency(
        self,
        dependency: str,
    ) -> PortalCredentials | None:
        ...

    def upsert(
        self,
        *,
        dependency: str,
        portal_username: str,
        encrypted_password: str,
    ) -> PortalCredentials:
        ...

    def record_test_result(
        self,
        *,
        dependency: str,
        tested_at: datetime,
        success: bool,
        code: str,
    ) -> PortalCredentials:
        ...
