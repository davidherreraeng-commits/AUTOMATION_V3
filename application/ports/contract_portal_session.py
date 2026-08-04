from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from application.ports.contract_portal import ContractPortal


@dataclass(frozen=True, slots=True)
class OpenedContractPortalSession:
    """Portal autenticado asociado a una única sesión de navegador."""

    portal: ContractPortal
    profile: str

    def __post_init__(self) -> None:
        normalized_profile = str(self.profile).strip()
        if not normalized_profile:
            raise ValueError("El perfil del portal es obligatorio.")
        object.__setattr__(self, "profile", normalized_profile)


class ContractPortalSessionFactory(Protocol):
    """Abre y cierra una sesión autenticada para un contrato."""

    def open(
        self,
        *,
        dependency: str,
    ) -> AbstractContextManager[OpenedContractPortalSession]:
        ...
