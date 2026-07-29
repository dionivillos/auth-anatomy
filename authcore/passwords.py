"""Password hashing (part 1: educational PBKDF2).

This module is deliberately hand-rolled to show what a password hash actually
stores. Argon2id (part 2, task 7) is the algorithm we use in production; PBKDF2
here exists to make the mechanics explicit and to give us a second algorithm to
exercise the PHC-prefix dispatch and rehash flow later.

Storage format (self-describing, single string):

    pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>

Every parameter needed to *verify* a password is embedded in the stored string,
so raising the iteration count later does not break old hashes: each hash is
checked with the iteration count it was created with.

`authcore` is pure: no I/O, no framework, no database. These functions take and
return plain strings.
"""

import base64
import binascii
import hashlib
import hmac
import secrets

# --- Parameters (see storage format above) -----------------------------------

_PREFIX = "pbkdf2_sha256"  # algorithm tag AND dispatch prefix for task 7
_ITERATIONS = 600_000  # OWASP recommendation for PBKDF2-HMAC-SHA256
_SALT_BYTES = 16  # 128 bits of per-hash salt, from `secrets`
_DKLEN = 32  # derived key length in bytes (matches SHA-256 output)

# Upper bound on the iteration count read from a stored hash. A crafted or
# corrupt record must not be able to force an unbounded PBKDF2 computation
# (a CPU-exhaustion denial of service) when we re-derive during verification.
_MAX_ITERATIONS = 2_000_000


def _b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.b64decode(text)


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    """Return the raw PBKDF2-HMAC-SHA256 derived key for these inputs.

    This single call is the entire cryptographic core; everything else in this
    module is just framing the result into a storable, self-describing string.
    """
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=_DKLEN)


def hash_password(password: str) -> str:
    """Hash a plaintext password into the self-describing storage string.

    A fresh random salt is drawn per call, so hashing the same password twice
    yields different strings: a stolen database never reveals which users share
    a password.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = _derive(password, salt, _ITERATIONS)
    return f"{_PREFIX}${_ITERATIONS}${_b64encode(salt)}${_b64encode(derived)}"


def verify_password(password: str, stored: str) -> bool:
    """Return True iff `password` matches the PBKDF2 hash in `stored`.

    The salt and iteration count are read from `stored` (not from the module
    constants), so a hash created with older parameters still verifies. The
    final comparison is constant-time to avoid leaking information through
    timing.

    Raises:
        ValueError: if `stored` is not a well-formed ``pbkdf2_sha256`` hash.
            Dispatching between algorithms by prefix arrives in task 7.
    """
    fields = stored.split("$", maxsplit=3)
    if len(fields) != 4:
        raise ValueError("not a pbkdf2_sha256 hash: expected 4 '$'-separated fields")

    prefix, iterations_raw, salt_b64, hash_b64 = fields
    if prefix != _PREFIX:
        raise ValueError(f"not a pbkdf2_sha256 hash: unexpected prefix {prefix!r}")

    try:
        iterations = int(iterations_raw)
    except ValueError as exc:
        raise ValueError("invalid iteration count in stored hash") from exc
    if not 0 < iterations <= _MAX_ITERATIONS:
        raise ValueError("iteration count in stored hash is out of the accepted range")

    try:
        salt = _b64decode(salt_b64)
        expected = _b64decode(hash_b64)
    except binascii.Error as exc:
        raise ValueError("corrupt base64 field in stored hash") from exc

    derived = _derive(password, salt, iterations)
    return hmac.compare_digest(derived, expected)
