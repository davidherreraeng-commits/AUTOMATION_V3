from __future__ import annotations

from typing import Protocol

from application.dto import PortalStepVerification
from domain.enums import ContractStep
from domain.models import ContractData


class ContractPortal(Protocol):
    """
    Puerto de salida hacia Gestión Transparente.

    La capa de aplicación trabaja con etapas semánticas y no conoce
    Selenium, WebDriver, selectores ni páginas concretas.
    """

    def execute_step(
        self,
        step: ContractStep,
        contract: ContractData,
    ) -> None:
        """
        Ejecuta la acción asociada a una etapa.
        """
        ...

    def verify_step(
        self,
        step: ContractStep,
        contract: ContractData,
    ) -> PortalStepVerification:
        """
        Verifica la postcondición de una etapa.
        """
        ...

    def recover(self) -> None:
        """
        Intenta recuperar el estado del navegador después de un error.
        """
        ...