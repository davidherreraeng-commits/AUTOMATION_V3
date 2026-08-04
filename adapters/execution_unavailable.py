from __future__ import annotations

from application.ports.batch_execution_runner import (
    BatchExecutionCallbacks,
)
from domain.models.contract_batch import ContractBatch


class UnavailableBatchExecutionRunner:
    """Guardia de seguridad mientras el adaptador Selenium no está conectado."""

    @property
    def name(self) -> str:
        return "selenium-gestion-transparente-pendiente"

    @property
    def available(self) -> bool:
        return False

    def run(
        self,
        *,
        batch: ContractBatch,
        callbacks: BatchExecutionCallbacks,
    ) -> None:
        raise RuntimeError(
            "El runner Selenium de lotes todavía no está configurado."
        )
