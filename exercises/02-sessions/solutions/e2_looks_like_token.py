"""Reference solution — Exercise 2 (token pre-validation)."""

_TOKEN_LENGTH = 32
_BASE32_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


def looks_like_token(value: str) -> bool:
    return len(value) == _TOKEN_LENGTH and all(char in _BASE32_ALPHABET for char in value)
