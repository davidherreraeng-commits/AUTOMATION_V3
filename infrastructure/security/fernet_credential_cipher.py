from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from domain.errors.portal_credential_errors import (
    PortalCredentialEncryptionError,
)


class FernetCredentialCipher:
    """Cifrado simétrico de contraseñas mediante Fernet."""

    def __init__(self, key: str) -> None:
        normalized = str(key).strip()
        if not normalized:
            raise PortalCredentialEncryptionError(
                "RPA_FERNET_KEY no está configurada."
            )
        try:
            self._fernet = Fernet(normalized.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as error:
            raise PortalCredentialEncryptionError(
                "RPA_FERNET_KEY no tiene un formato Fernet válido."
            ) from error

    def encrypt(self, plaintext: str) -> str:
        value = str(plaintext)
        if not value:
            raise ValueError("El secreto que se va a cifrar está vacío.")
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        token = str(ciphertext).strip()
        if not token:
            raise ValueError("El texto cifrado está vacío.")
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError) as error:
            raise PortalCredentialEncryptionError(
                "No fue posible descifrar el secreto almacenado."
            ) from error
