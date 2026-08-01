import base64

from authcore import tokens


def test_generate_has_at_least_160_bits_of_entropy() -> None:
    token = tokens.generate()

    # base32 encodes 5 bits per character; 32 chars => 160 bits.
    assert len(token) >= 32
    decoded = base64.b32decode(token)
    assert len(decoded) * 8 >= 160


def test_generate_is_valid_base32() -> None:
    # Must decode without raising.
    base64.b32decode(tokens.generate())


def test_generate_is_unique_across_many_calls() -> None:
    produced = {tokens.generate() for _ in range(1000)}

    assert len(produced) == 1000


def test_sha256_hex_is_deterministic() -> None:
    assert tokens.sha256_hex("a-token") == tokens.sha256_hex("a-token")


def test_sha256_hex_is_64_hex_chars() -> None:
    digest = tokens.sha256_hex("a-token")

    assert len(digest) == 64
    int(digest, 16)  # parses as hex


def test_sha256_hex_differs_for_different_input() -> None:
    assert tokens.sha256_hex("token-a") != tokens.sha256_hex("token-b")


def test_sha256_hex_matches_known_vector() -> None:
    # The canonical SHA-256("abc") test vector.
    assert (
        tokens.sha256_hex("abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_constant_time_compare_true_for_equal() -> None:
    assert tokens.constant_time_compare("secret-hash", "secret-hash") is True


def test_constant_time_compare_false_for_different() -> None:
    assert tokens.constant_time_compare("secret-hash", "secret-hasH") is False
    assert tokens.constant_time_compare("secret", "secret-longer") is False


def test_presented_token_matches_stored_hash() -> None:
    # The real usage: hash a generated token, then match it later by re-hashing.
    token = tokens.generate()
    stored = tokens.sha256_hex(token)

    assert tokens.constant_time_compare(stored, tokens.sha256_hex(token)) is True
