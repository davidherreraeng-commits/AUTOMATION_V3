from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, encoded_hash: str) -> bool: ...

    def needs_rehash(self, encoded_hash: str) -> bool: ...
