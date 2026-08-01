"""Opaque security tokens: generation, hashing, constant-time comparison.

Session tokens (and later the one-time email tokens) are high-entropy random
strings shown to the client once. The server stores only their SHA-256 hash, so
a database leak never exposes a usable token: an attacker would have to invert
SHA-256. When a token arrives, hash it and look that hash up.

`authcore` is pure: plain values in, plain values out.
"""

import base64
import hashlib
import hmac
import secrets

# 20 bytes = 160 bits of entropy, the minimum for a session token. base32 of
# 20 bytes is exactly 32 characters with no '=' padding.
_TOKEN_BYTES = 20


def generate() -> str:
    """Return a new high-entropy token (base32, >= 160 bits).

    Bytes come from `secrets` (a CSPRNG, never `random`). base32 keeps the token
    to a safe, case-insensitive alphabet (A-Z, 2-7) with no cookie/URL-hostile
    characters.
    """
    return base64.b32encode(secrets.token_bytes(_TOKEN_BYTES)).decode("ascii")


def sha256_hex(token: str) -> str:
    """Return the hex SHA-256 of `token` — the value stored in the database.

    Deterministic on purpose: the same token always hashes to the same value,
    which is how a presented token is matched to a stored hash.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time (no early exit on first mismatch).

    Never use `==` on secret-derived values — its timing leaks how many leading
    characters matched.
    """
    return hmac.compare_digest(a, b)
