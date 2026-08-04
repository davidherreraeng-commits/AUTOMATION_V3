"""Compatibilidad para imports históricos de la máquina de estados.

La implementación pertenece al dominio. Los nuevos módulos deben importar
``ContractStateMachine`` desde ``domain.services.contract_state_machine``.
"""

from domain.services.contract_state_machine import ContractStateMachine

__all__ = ["ContractStateMachine"]
