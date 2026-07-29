from authcore import passwords


def test_hash_has_self_describing_format() -> None:
    stored = passwords.hash_password("correct horse battery staple")

    parts = stored.split("$")
    assert len(parts) == 4
    prefix, iterations, salt_b64, hash_b64 = parts
    assert prefix == "pbkdf2_sha256"
    assert iterations == "600000"
    assert salt_b64 and hash_b64


def test_hash_never_contains_the_plaintext() -> None:
    secret = "super-secret-password"
    stored = passwords.hash_password(secret)

    assert secret not in stored


def test_verify_accepts_the_right_password() -> None:
    stored = passwords.hash_password("s3cur3-p4ss")

    assert passwords.verify_password("s3cur3-p4ss", stored) is True


def test_verify_rejects_the_wrong_password() -> None:
    stored = passwords.hash_password("s3cur3-p4ss")

    assert passwords.verify_password("wrong-password", stored) is False


def test_same_password_yields_different_hashes() -> None:
    # A fresh random salt per hash means identical passwords hash differently,
    # so a stolen database does not reveal which users share a password.
    first = passwords.hash_password("same-password")
    second = passwords.hash_password("same-password")

    assert first != second
    # ...yet both still verify.
    assert passwords.verify_password("same-password", first) is True
    assert passwords.verify_password("same-password", second) is True


def test_tampered_hash_is_rejected() -> None:
    stored = passwords.hash_password("original")
    prefix, iterations, salt_b64, hash_b64 = stored.split("$")
    # Flip the first character of the stored digest.
    flipped = "B" if hash_b64[0] != "B" else "C"
    tampered = "$".join([prefix, iterations, salt_b64, flipped + hash_b64[1:]])

    assert passwords.verify_password("original", tampered) is False
