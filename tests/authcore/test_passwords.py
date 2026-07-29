import pytest
from argon2 import PasswordHasher, Type

from authcore import passwords

# --- Argon2id: the production algorithm for new hashes ------------------------


def test_hash_password_uses_argon2id() -> None:
    stored = passwords.hash_password("correct horse battery staple")

    assert stored.startswith("$argon2id$")


def test_argon2_round_trip() -> None:
    stored = passwords.hash_password("s3cur3-p4ss")

    assert passwords.verify_password("s3cur3-p4ss", stored) is True


def test_argon2_wrong_password_is_rejected() -> None:
    stored = passwords.hash_password("s3cur3-p4ss")

    assert passwords.verify_password("wrong-password", stored) is False


def test_argon2_same_password_yields_different_hashes() -> None:
    # Argon2's built-in random salt gives distinct hashes for the same password.
    assert passwords.hash_password("same") != passwords.hash_password("same")


# --- Legacy PBKDF2: verify-only from part 2 onward ----------------------------


def test_pbkdf2_hash_has_self_describing_format() -> None:
    stored = passwords._hash_pbkdf2("correct horse battery staple")

    prefix, iterations, salt_b64, hash_b64 = stored.split("$")
    assert prefix == "pbkdf2_sha256"
    assert iterations == "600000"
    assert salt_b64 and hash_b64


def test_pbkdf2_hash_never_contains_the_plaintext() -> None:
    secret = "super-secret-password"

    assert secret not in passwords._hash_pbkdf2(secret)


def test_pbkdf2_same_password_yields_different_hashes() -> None:
    first = passwords._hash_pbkdf2("same-password")
    second = passwords._hash_pbkdf2("same-password")

    assert first != second
    assert passwords._verify_pbkdf2("same-password", first) is True
    assert passwords._verify_pbkdf2("same-password", second) is True


def test_pbkdf2_tampered_hash_is_rejected() -> None:
    stored = passwords._hash_pbkdf2("original")
    prefix, iterations, salt_b64, hash_b64 = stored.split("$")
    flipped = "B" if hash_b64[0] != "B" else "C"
    tampered = "$".join([prefix, iterations, salt_b64, flipped + hash_b64[1:]])

    assert passwords._verify_pbkdf2("original", tampered) is False


# --- Dispatch: verify_password picks the algorithm by prefix ------------------


def test_verify_dispatches_to_pbkdf2() -> None:
    legacy = passwords._hash_pbkdf2("legacy-pass")

    assert passwords.verify_password("legacy-pass", legacy) is True
    assert passwords.verify_password("nope", legacy) is False


def test_verify_unknown_format_raises() -> None:
    with pytest.raises(ValueError):
        passwords.verify_password("whatever", "bcrypt$2b$something")


# --- needs_rehash: flag stale hashes for upgrade ------------------------------


def test_needs_rehash_true_for_legacy_pbkdf2() -> None:
    legacy = passwords._hash_pbkdf2("legacy-pass")

    assert passwords.needs_rehash(legacy) is True


def test_needs_rehash_false_for_fresh_argon2() -> None:
    fresh = passwords.hash_password("fresh-pass")

    assert passwords.needs_rehash(fresh) is False


def test_needs_rehash_true_for_weaker_argon2() -> None:
    # An Argon2id hash made with weaker-than-current parameters must be flagged.
    weak_hasher = PasswordHasher(
        time_cost=1, memory_cost=8, parallelism=1, hash_len=32, salt_len=16, type=Type.ID
    )
    weak = weak_hasher.hash("weak-pass")

    assert passwords.needs_rehash(weak) is True


def test_needs_rehash_unknown_format_raises() -> None:
    with pytest.raises(ValueError):
        passwords.needs_rehash("bcrypt$2b$something")


# --- Acceptance: a PBKDF2 password verifies and is flagged for upgrade --------


def test_pbkdf2_password_verifies_then_upgrades_to_argon2() -> None:
    # A user whose password was stored with the old algorithm...
    legacy = passwords._hash_pbkdf2("my-password")

    # ...still logs in, and the hash is flagged as needing an upgrade.
    assert passwords.verify_password("my-password", legacy) is True
    assert passwords.needs_rehash(legacy) is True

    # The service re-hashes the plaintext it just verified: now Argon2id, fresh.
    upgraded = passwords.hash_password("my-password")
    assert upgraded.startswith("$argon2id$")
    assert passwords.verify_password("my-password", upgraded) is True
    assert passwords.needs_rehash(upgraded) is False
