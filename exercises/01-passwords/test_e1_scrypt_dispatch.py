import pytest

from authcore import passwords
from e1_scrypt_dispatch import (
    SCRYPT_PREFIX,
    hash_scrypt,
    verify_any,
    verify_scrypt,
)


def test_scrypt_hash_has_self_describing_format() -> None:
    stored = hash_scrypt("a-good-passphrase")

    fields = stored.split("$")
    assert len(fields) == 6
    assert fields[0] == SCRYPT_PREFIX
    assert all(fields[1:])  # n, r, p, salt, hash all present


def test_scrypt_round_trip() -> None:
    stored = hash_scrypt("a-good-passphrase")

    assert verify_scrypt("a-good-passphrase", stored) is True
    assert verify_scrypt("wrong", stored) is False


def test_scrypt_same_password_yields_different_hashes() -> None:
    assert hash_scrypt("same") != hash_scrypt("same")


def test_verify_any_handles_scrypt() -> None:
    assert verify_any("pw-scrypt", hash_scrypt("pw-scrypt")) is True


def test_verify_any_delegates_to_argon2() -> None:
    argon2_hash = passwords.hash_password("pw-argon2")

    assert verify_any("pw-argon2", argon2_hash) is True
    assert verify_any("nope", argon2_hash) is False


def test_verify_any_delegates_to_legacy_pbkdf2() -> None:
    pbkdf2_hash = passwords._hash_pbkdf2("pw-pbkdf2")

    assert verify_any("pw-pbkdf2", pbkdf2_hash) is True


def test_scrypt_verify_rejects_malformed() -> None:
    with pytest.raises(ValueError):
        verify_scrypt("x", "scrypt$not-enough-fields")
