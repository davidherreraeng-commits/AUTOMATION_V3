from __future__ import annotations

import base64
import hashlib
import hmac
import os


class ScryptPasswordHasher:
    """
    Genera hashes nuevos con scrypt y acepta hashes bcrypt heredados.

    Cuando un usuario heredado inicia sesión correctamente, el servicio
    de autenticación reemplaza automáticamente su hash bcrypt por scrypt.
    """

    PREFIX = "scrypt"
    N = 2**14
    R = 8
    P = 1
    DKLEN = 64
    SALT_BYTES = 16

    def hash(self, password: str) -> str:
        normalized = self._validate_password(password)
        salt = os.urandom(self.SALT_BYTES)
        derived = hashlib.scrypt(
            normalized.encode("utf-8"),
            salt=salt,
            n=self.N,
            r=self.R,
            p=self.P,
            dklen=self.DKLEN,
        )
        salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii")
        hash_b64 = base64.urlsafe_b64encode(derived).decode("ascii")
        return (
            f"{self.PREFIX}$n={self.N},r={self.R},p={self.P}"
            f"${salt_b64}${hash_b64}"
        )

    def verify(self, password: str, encoded_hash: str) -> bool:
        try:
            if encoded_hash.startswith(f"{self.PREFIX}$"):
                return self._verify_scrypt(password, encoded_hash)
            if encoded_hash.startswith(("$2a$", "$2b$", "$2y$")):
                return self._verify_legacy_bcrypt(password, encoded_hash)
        except (ValueError, TypeError, UnicodeError):
            return False
        return False

    def needs_rehash(self, encoded_hash: str) -> bool:
        if not encoded_hash.startswith(f"{self.PREFIX}$"):
            return True
        try:
            params = encoded_hash.split("$", 3)[1]
            parsed = self._parse_params(params)
        except (ValueError, IndexError):
            return True
        return parsed != (self.N, self.R, self.P)

    def _verify_scrypt(self, password: str, encoded_hash: str) -> bool:
        normalized = self._validate_password(password)
        prefix, params, salt_b64, hash_b64 = encoded_hash.split("$", 3)
        if prefix != self.PREFIX:
            return False

        n, r, p = self._parse_params(params)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(hash_b64.encode("ascii"))
        actual = hashlib.scrypt(
            normalized.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def _parse_params(value: str) -> tuple[int, int, int]:
        values: dict[str, int] = {}
        for part in value.split(","):
            key, raw = part.split("=", 1)
            values[key] = int(raw)
        return values["n"], values["r"], values["p"]

    @staticmethod
    def _verify_legacy_bcrypt(
        password: str,
        encoded_hash: str,
    ) -> bool:
        try:
            import bcrypt  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError(
                "Instala bcrypt para validar usuarios heredados."
            ) from error

        return bcrypt.checkpw(
            password.encode("utf-8"),
            encoded_hash.encode("utf-8"),
        )

    @staticmethod
    def _validate_password(password: str) -> str:
        normalized = str(password)
        if not normalized:
            raise ValueError("La contraseña no puede estar vacía.")
        if len(normalized) > 128:
            raise ValueError(
                "La contraseña no puede superar 128 caracteres."
            )
        return normalized
