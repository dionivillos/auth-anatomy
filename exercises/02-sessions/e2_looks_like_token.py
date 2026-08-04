"""Exercise 2 — Reject junk cookies before touching the database.

Difficulty: ★★☆

Every request carries the session cookie, and `validate_session` hashes it and
does a database lookup. Before spending that lookup, it is cheap and useful to
reject values that could not possibly be one of our tokens — a truncated cookie,
random garbage, an attacker's probe.

Our tokens are exactly 32 characters from the base32 alphabet (`A`–`Z`, `2`–`7`;
see `authcore.tokens`). Implement a structural check for that shape. It is not a
security check on its own — it does not prove the token is valid — just a fast
pre-filter.

Complete `looks_like_token` so `test_e2_looks_like_token.py` passes.
Reference solution: `solutions/e2_looks_like_token.py`.
"""

# Our base32 tokens: 20 random bytes -> exactly 32 characters, no padding.
_TOKEN_LENGTH = 32
_BASE32_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


def looks_like_token(value: str) -> bool:
    """Return True iff `value` is shaped like one of our tokens.

    TODO(you): return True only when both hold:
      1. `len(value) == _TOKEN_LENGTH`.
      2. Every character of `value` is in `_BASE32_ALPHABET` (case-sensitive —
         our tokens are uppercase). `all(...)` over the characters works well.
    """
    return (len(value) == _TOKEN_LENGTH) and (all(v in _BASE32_ALPHABET for v in value))
