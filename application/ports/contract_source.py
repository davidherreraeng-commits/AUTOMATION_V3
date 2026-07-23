from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from application.dto import ContractImportResult


class ContractSource(Protocol):
    """
    Puerto de entrada para cualquier fuente de contratos.

    La aplicación no necesita saber si los datos provienen de Excel,
    CSV, Google Sheets o una base de datos.
    """

    def read(self) -> Iterable[ContractImportResult]:
        ...