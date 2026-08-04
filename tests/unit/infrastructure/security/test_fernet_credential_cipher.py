from cryptography.fernet import Fernet
import pytest

from domain.errors.portal_credential_errors import (
    PortalCredentialEncryptionError,
)
from infrastructure.security.fernet_credential_cipher import (
    FernetCredentialCipher,
)


def test_should_encrypt_and_decrypt_without_exposing_plaintext() -> None:
    cipher = FernetCredentialCipher(Fernet.generate_key().decode("ascii"))

    encrypted = cipher.encrypt("ClavePortal2026")

    assert encrypted != "ClavePortal2026"
    assert cipher.decrypt(encrypted) == "ClavePortal2026"


def test_should_produce_different_tokens_for_same_password() -> None:
    cipher = FernetCredentialCipher(Fernet.generate_key().decode("ascii"))

    first = cipher.encrypt("MismaClave")
    second = cipher.encrypt("MismaClave")

    assert first != second
    assert cipher.decrypt(first) == cipher.decrypt(second) == "MismaClave"


def test_should_reject_invalid_key() -> None:
    with pytest.raises(PortalCredentialEncryptionError):
        FernetCredentialCipher("clave-invalida")
