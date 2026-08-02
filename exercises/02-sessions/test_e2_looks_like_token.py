import pytest

from authcore import tokens
from e2_looks_like_token import looks_like_token


def test_accepts_a_real_generated_token() -> None:
    assert looks_like_token(tokens.generate()) is True


def test_rejects_wrong_length() -> None:
    assert looks_like_token("ABC") is False
    assert looks_like_token("A" * 33) is False


@pytest.mark.parametrize("value", ["a" * 32, "0" * 32, "1" * 32, "A" * 31 + "!"])
def test_rejects_invalid_characters(value: str) -> None:
    # Lowercase and the digits 0/1/8/9 are outside the base32 alphabet.
    assert looks_like_token(value) is False


def test_rejects_empty() -> None:
    assert looks_like_token("") is False
