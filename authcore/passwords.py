"""Password hashing: Argon2id (production) with transparent upgrade from PBKDF2.

New passwords are hashed with Argon2id (argon2-cffi). Legacy PBKDF2 hashes from
part 1 still verify, and ``needs_rehash`` flags them so the service layer can
upgrade them to Argon2id on the next successful login — the verify-then-rehash
pattern, which works because the plaintext is only available at that moment.

Dispatch is by the PHC-style prefix of the stored string:

  - ``$argon2id$...``     -> Argon2id
  - ``pbkdf2_sha256$...`` -> legacy educational PBKDF2

`authcore` is pure: no I/O, no framework, no database. These functions take and
return plain strings.
"""

import base64
import binascii
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# --- Argon2id (production algorithm for new hashes) ---------------------------

# OWASP-recommended Argon2id parameters. memory_cost is in KiB (19456 KiB ~= 19
# MiB); time_cost is the number of iterations; parallelism is the lane count.
_ARGON2_TIME_COST = 2
_ARGON2_MEMORY_COST = 19_456
_ARGON2_PARALLELISM = 1
_ARGON2_HASH_LEN = 32
_ARGON2_SALT_LEN = 16
_ARGON2_PREFIX = "$argon2"  # covers $argon2id$, $argon2i$, $argon2d$

# One configured hasher, reused for every call. It also knows the "current"
# parameters, which is what check_needs_rehash() compares a stored hash against.
_argon2_hasher = PasswordHasher(
    time_cost=_ARGON2_TIME_COST,
    memory_cost=_ARGON2_MEMORY_COST,
    parallelism=_ARGON2_PARALLELISM,
    hash_len=_ARGON2_HASH_LEN,
    salt_len=_ARGON2_SALT_LEN,
    type=Type.ID,
)


def _hash_argon2(password: str) -> str:
    """Hash with Argon2id, returning a self-describing PHC string."""
    return _argon2_hasher.hash(password)


def _verify_argon2(password: str, stored: str) -> bool:
    """Verify an Argon2id PHC string; False on mismatch, ValueError if malformed."""
    try:
        return _argon2_hasher.verify(stored, password)
    except VerifyMismatchError:
        return False
    except (InvalidHashError, VerificationError) as exc:
        raise ValueError("invalid argon2 hash") from exc


# --- Legacy educational PBKDF2 (verify-only from here on) --------------

_PBKDF2_PREFIX = "pbkdf2_sha256"  # algorithm tag AND dispatch prefix
_PBKDF2_ITERATIONS = 600_000  # OWASP recommendation for PBKDF2-HMAC-SHA256
_PBKDF2_SALT_BYTES = 16  # 128 bits of per-hash salt, from `secrets`
_PBKDF2_DKLEN = 32  # derived key length in bytes (matches SHA-256 output)

# Upper bound on the iteration count read from a stored hash. A crafted or
# corrupt record must not be able to force an unbounded PBKDF2 computation
# (a CPU-exhaustion denial of service) when we re-derive during verification.
_PBKDF2_MAX_ITERATIONS = 2_000_000


def _b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.b64decode(text)


def _pbkdf2_derive(password: str, salt: bytes, iterations: int) -> bytes:
    """Return the raw PBKDF2-HMAC-SHA256 derived key for these inputs."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, dklen=_PBKDF2_DKLEN
    )


def _hash_pbkdf2(password: str) -> str:
    """Hash a password into the self-describing PBKDF2 storage string.

    Kept for tests and to generate legacy hashes; new production hashes go
    through :func:`hash_password` (Argon2id).
    """
    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    derived = _pbkdf2_derive(password, salt, _PBKDF2_ITERATIONS)
    return f"{_PBKDF2_PREFIX}${_PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(derived)}"


def _verify_pbkdf2(password: str, stored: str) -> bool:
    """Verify a PBKDF2 storage string, reading salt/iterations from it."""
    fields = stored.split("$", maxsplit=3)
    if len(fields) != 4:
        raise ValueError("not a pbkdf2_sha256 hash: expected 4 '$'-separated fields")

    prefix, iterations_raw, salt_b64, hash_b64 = fields
    if prefix != _PBKDF2_PREFIX:
        raise ValueError(f"not a pbkdf2_sha256 hash: unexpected prefix {prefix!r}")

    try:
        iterations = int(iterations_raw)
    except ValueError as exc:
        raise ValueError("invalid iteration count in stored hash") from exc
    if not 0 < iterations <= _PBKDF2_MAX_ITERATIONS:
        raise ValueError("iteration count in stored hash is out of the accepted range")

    try:
        salt = _b64decode(salt_b64)
        expected = _b64decode(hash_b64)
    except binascii.Error as exc:
        raise ValueError("corrupt base64 field in stored hash") from exc

    derived = _pbkdf2_derive(password, salt, iterations)
    return hmac.compare_digest(derived, expected)


# --- Public API ---------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a new password. Always Argon2id — the production algorithm."""
    return _hash_argon2(password)


def verify_password(password: str, stored: str) -> bool:
    """Verify `password` against `stored`, dispatching on the stored prefix.

    Argon2id and legacy PBKDF2 hashes are told apart by their prefix; the
    matching wrapper performs the actual constant-time comparison.

    Raises:
        ValueError: if `stored` is not a recognised hash format.
    """
    if stored.startswith(_PBKDF2_PREFIX + "$"):
        return _verify_pbkdf2(password, stored)
    elif stored.startswith(_ARGON2_PREFIX):
        return _verify_argon2(password, stored)
    else:
        raise ValueError("unknown or unsupported password hash format")


def needs_rehash(stored: str) -> bool:
    """Return True if `stored` should be re-hashed to the current Argon2id params.

    A legacy PBKDF2 hash always needs upgrading to Argon2id. An Argon2id hash
    needs it only when its embedded cost parameters differ from the ones
    configured now. Callers run this right after a successful verify_password
    and, if it returns True, re-hash the plaintext they still hold and overwrite
    the stored value.

    Raises:
        ValueError: if `stored` is not a recognised hash format.
    """
    if stored.startswith(_PBKDF2_PREFIX + "$"):
        return True
    elif stored.startswith(_ARGON2_PREFIX):
        return _argon2_hasher.check_needs_rehash(stored)
    else:
        raise ValueError("unknown or unsupported password hash format")
