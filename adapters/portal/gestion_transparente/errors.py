from __future__ import annotations

from domain.enums import ContractStep
from domain.errors import PortalStructureChangedError


class UnsupportedPortalStepError(
    PortalStructureChangedError
):
    """
    La implementación de Gestión Transparente no tiene un componente
    registrado para la etapa recibida.
    """

    def __init__(
        self,
        step: ContractStep,
    ) -> None:
        self.step = step

        super().__init__(
            "La etapa no puede ser ejecutada directamente por el "
            f"adaptador de Gestión Transparente: {step.value}.",
            metadata={
                "step": step.value,
            },
        )


class PortalVerificationMismatchError(
    PortalStructureChangedError
):
    """
    Un componente devolvió una verificación correspondiente a una etapa
    diferente de la solicitada.
    """

    def __init__(
        self,
        *,
        requested_step: ContractStep,
        returned_step: ContractStep,
    ) -> None:
        self.requested_step = requested_step
        self.returned_step = returned_step

        super().__init__(
            "El componente del portal devolvió una verificación "
            "inconsistente. "
            f"Etapa solicitada: {requested_step.value}. "
            f"Etapa retornada: {returned_step.value}.",
            metadata={
                "requested_step": requested_step.value,
                "returned_step": returned_step.value,
            },
        )