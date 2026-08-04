from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from uuid import UUID

from application.dto.execution_evidence import ContractExecutionEvidence
from application.ports.execution_evidence_repository import (
    ExecutionEvidenceRepositoryError,
)
from domain.enums import ExecutionMode


class JsonExecutionEvidenceRepository:
    """Persistencia atómica de evidencias, separada de los checkpoints reales."""

    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)
        self._lock = Lock()

    def initialize(self) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)

    def save(self, evidence: ContractExecutionEvidence) -> None:
        self.initialize()
        destination = self._path(evidence.correlation_id)
        temporary = destination.with_suffix(".json.tmp")
        payload = json.dumps(
            evidence.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        try:
            with self._lock:
                temporary.write_text(payload, encoding="utf-8")
                os.replace(temporary, destination)
        except OSError as error:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise ExecutionEvidenceRepositoryError(
                "No fue posible persistir la evidencia contractual."
            ) from error

    def get(self, correlation_id: UUID) -> ContractExecutionEvidence | None:
        path = self._path(correlation_id)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return ContractExecutionEvidence.from_dict(payload)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            raise ExecutionEvidenceRepositoryError(
                f"La evidencia '{correlation_id}' está dañada o no puede leerse."
            ) from error

    def get_latest(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
        mode: ExecutionMode | None = None,
    ) -> ContractExecutionEvidence | None:
        records = self.list_for_item(batch_id=batch_id, item_id=item_id)
        filtered = (
            tuple(record for record in records if record.mode is mode)
            if mode is not None
            else records
        )
        return filtered[0] if filtered else None

    def list_for_item(
        self,
        *,
        batch_id: UUID,
        item_id: UUID,
    ) -> tuple[ContractExecutionEvidence, ...]:
        self.initialize()
        records: list[ContractExecutionEvidence] = []
        for path in self._directory.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                record = ContractExecutionEvidence.from_dict(payload)
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
                raise ExecutionEvidenceRepositoryError(
                    f"La evidencia '{path.name}' está dañada o no puede leerse."
                ) from error
            if record.batch_id == batch_id and record.item_id == item_id:
                records.append(record)
        records.sort(key=lambda record: record.completed_at, reverse=True)
        return tuple(records)

    def _path(self, correlation_id: UUID) -> Path:
        return self._directory / f"{correlation_id}.json"
