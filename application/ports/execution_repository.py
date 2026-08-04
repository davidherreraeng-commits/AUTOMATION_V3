<<<<<<< HEAD
from __future__ import annotations

from collections.abc import Collection
from typing import Protocol
from uuid import UUID

from domain.enums import ExecutionStatus
from domain.models import ContractExecution


class ExecutionRepositoryError(RuntimeError):
    """
    Error general del puerto de persistencia de ejecuciones.

    La capa de aplicación puede capturarlo sin conocer si la
    implementación concreta utiliza SQLite, PostgreSQL u otro motor.
    """


class ExecutionIdentityConflictError(
    ExecutionRepositoryError
):
    """
    Ya existe otra ejecución para la misma combinación de contrato
    y dependencia.
    """


class ExecutionRepository(Protocol):
    """
    Puerto para almacenar y recuperar ejecuciones contractuales.

    Las implementaciones deben conservar completamente el checkpoint
    representado por ContractExecution.
    """

    def initialize(self) -> None:
        """
        Crea o actualiza la estructura necesaria de persistencia.
        """
        ...

    def save(
        self,
        execution: ContractExecution,
    ) -> None:
        """
        Inserta una ejecución nueva o actualiza su estado actual.
        """
        ...

    def get_by_id(
        self,
        execution_id: UUID,
    ) -> ContractExecution | None:
        """
        Recupera una ejecución por su identificador.
        """
        ...

    def get_by_contract(
        self,
        contract_number: str,
        dependency: str,
    ) -> ContractExecution | None:
        """
        Recupera la ejecución asociada a un contrato y dependencia.
        """
        ...

    def list_by_status(
        self,
        statuses: Collection[ExecutionStatus] | None = None,
    ) -> tuple[ContractExecution, ...]:
        """
        Lista ejecuciones, opcionalmente filtradas por estado.
        """
=======
from __future__ import annotations

from collections.abc import Collection
from typing import Protocol
from uuid import UUID

from domain.enums import ExecutionStatus
from domain.models import ContractExecution


class ExecutionRepositoryError(RuntimeError):
    """
    Error general del puerto de persistencia de ejecuciones.

    La capa de aplicación puede capturarlo sin conocer si la
    implementación concreta utiliza SQLite, PostgreSQL u otro motor.
    """


class ExecutionIdentityConflictError(
    ExecutionRepositoryError
):
    """
    Ya existe otra ejecución para la misma combinación de contrato
    y dependencia.
    """


class ExecutionRepository(Protocol):
    """
    Puerto para almacenar y recuperar ejecuciones contractuales.

    Las implementaciones deben conservar completamente el checkpoint
    representado por ContractExecution.
    """

    def initialize(self) -> None:
        """
        Crea o actualiza la estructura necesaria de persistencia.
        """
        ...

    def save(
        self,
        execution: ContractExecution,
    ) -> None:
        """
        Inserta una ejecución nueva o actualiza su estado actual.
        """
        ...

    def get_by_id(
        self,
        execution_id: UUID,
    ) -> ContractExecution | None:
        """
        Recupera una ejecución por su identificador.
        """
        ...

    def get_by_contract(
        self,
        contract_number: str,
        dependency: str,
    ) -> ContractExecution | None:
        """
        Recupera la ejecución asociada a un contrato y dependencia.
        """
        ...

    def list_by_status(
        self,
        statuses: Collection[ExecutionStatus] | None = None,
    ) -> tuple[ContractExecution, ...]:
        """
        Lista ejecuciones, opcionalmente filtradas por estado.
        """
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
        ...