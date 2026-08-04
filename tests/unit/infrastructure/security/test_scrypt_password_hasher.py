from infrastructure.security.scrypt_password_hasher import (
    ScryptPasswordHasher,
)


def test_should_hash_and_verify_password() -> None:
    hasher = ScryptPasswordHasher()

    encoded = hasher.hash("ClaveSegura2026")

    assert encoded.startswith("scrypt$")
    assert hasher.verify("ClaveSegura2026", encoded) is True
    assert hasher.verify("otra-clave", encoded) is False
    assert hasher.needs_rehash(encoded) is False


def test_should_reject_unknown_hash_format() -> None:
    hasher = ScryptPasswordHasher()

    assert hasher.verify("clave", "formato-desconocido") is False
    assert hasher.needs_rehash("formato-desconocido") is True
