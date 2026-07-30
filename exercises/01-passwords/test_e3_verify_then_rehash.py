from authcore import passwords
from e3_verify_then_rehash import AuthResult, authenticate


def test_wrong_password_fails_with_no_upgrade() -> None:
    stored = passwords.hash_password("right")

    result = authenticate(stored, "wrong")

    assert result == AuthResult(ok=False, new_hash=None)


def test_current_argon2_succeeds_without_upgrade() -> None:
    stored = passwords.hash_password("my-password")

    result = authenticate(stored, "my-password")

    assert result.ok is True
    assert result.new_hash is None


def test_legacy_pbkdf2_succeeds_and_yields_an_upgrade() -> None:
    legacy = passwords._hash_pbkdf2("my-password")

    result = authenticate(legacy, "my-password")

    assert result.ok is True
    assert result.new_hash is not None
    assert result.new_hash.startswith("$argon2id$")


def test_upgraded_hash_is_valid_and_no_longer_needs_rehash() -> None:
    legacy = passwords._hash_pbkdf2("my-password")

    result = authenticate(legacy, "my-password")

    assert result.new_hash is not None
    # The persisted upgrade must itself verify the same password...
    assert passwords.verify_password("my-password", result.new_hash) is True
    # ...and must not trigger another upgrade next time.
    assert passwords.needs_rehash(result.new_hash) is False
