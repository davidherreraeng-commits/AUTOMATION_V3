from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol
from uuid import UUID

from domain.enums.batch_status import BatchContractStatus
from domain.models.contract_batch import ContractBatch


@dataclass(frozen=True, slots=True)
class BatchExecutionCallbacks:
    """Callbacks usados por un runner para reportar progreso persistible."""

    mark_contract_started: Callable[[UUID], None]
    mark_contract_finished: Callable[[UUID, BatchContractStatus, str | None], None]


class BatchExecutionRunner(Protocol):
    """Ejecutor concreto de un lote.

    6C-1 define el contrato y el control de ciclo de vida. El adaptador
    Selenium real será conectado en el incremento 6C-2.
    """

    @property
    def name(self) -> str:
        ...

    @property
    def available(self) -> bool:
        ...

    def run(
        self,
        *,
        batch: ContractBatch,
        callbacks: BatchExecutionCallbacks,
    ) -> None:
        ...
