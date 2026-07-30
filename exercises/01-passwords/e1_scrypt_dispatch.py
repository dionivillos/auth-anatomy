"""Exercise 1 — Add a third algorithm (scrypt) to the dispatch.

Difficulty: ★★☆

You are integrating with a legacy system whose password hashes use **scrypt**
(RFC 7914), stored in a self-describing format:

    scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>

Your job: implement scrypt hashing/verification AND a `verify_any` that routes a
stored hash to the right verifier — scrypt here, or Argon2id/PBKDF2 by reusing
`authcore.passwords.verify_password`. You are *extending* the dispatch idea from
the module without touching `authcore`.

Complete the three functions below so `test_e1_scrypt_dispatch.py` passes.
Reference solution: `solutions/e1_scrypt_dispatch.py`.
"""

import base64
import binascii
import hashlib
import hmac
import secrets

from authcore import passwords

SCRYPT_PREFIX = "scrypt"

# scrypt cost parameters (RFC 7914 names): n = CPU/memory cost (a power of two),
# r = block size, p = parallelisation.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_SALT_BYTES = 16
_SCRYPT_DKLEN = 32


def hash_scrypt(password: str) -> str:
    """Hash `password` with scrypt into the self-describing format above.

    TODO(you):
      1. Draw a fresh salt with `secrets.token_bytes(_SCRYPT_SALT_BYTES)`.
      2. Derive the key with `hashlib.scrypt(password.encode("utf-8"), salt=...,
         n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_DKLEN)`.
      3. Return f"{SCRYPT_PREFIX}${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}$"
         plus the base64 of the salt and of the derived key.
    """
    salt = secrets.token_bytes(_SCRYPT_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, 
        r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_DKLEN
        )
    salt_b64 = passwords._b64encode(salt)
    hash_b64 = passwords._b64encode(derived)
    
    return f"{SCRYPT_PREFIX}${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt_b64}${hash_b64}"


def verify_scrypt(password: str, stored: str) -> bool:
    """Verify a scrypt hash, reading n/r/p and the salt from `stored`.

    TODO(you):
      1. Split into exactly 6 fields; the first must equal SCRYPT_PREFIX.
      2. Parse n, r, p as ints and base64-decode the salt and expected hash.
      3. Re-derive with the parsed parameters and compare with
         `hmac.compare_digest` (constant time).
      4. Raise ValueError if `stored` is not a well-formed scrypt hash.
    """
    fields = stored.split("$", maxsplit=5)
    if len(fields) != 6:
        raise ValueError("expected 6 fields")

    prefix, n_raw, r_raw, p_raw, salt_b64, hash_b64 = fields
    if prefix != SCRYPT_PREFIX:
        raise ValueError(f"unexpected prefyx: {prefix}")

    try:
        n, r, p = int(n_raw), int(r_raw), int(p_raw)
    except ValueError as exc:
        raise ValueError("invalid values in n, r, p") from exc

    try:
        salt = passwords._b64decode(salt_b64)
        expected = passwords._b64decode(hash_b64)
    except binascii.Error as exc:
        raise ValueError("corrupt base64") from exc

    
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=_SCRYPT_DKLEN
        )

    return hmac.compare_digest(derived, expected)
    

def verify_any(password: str, stored: str) -> bool:
    """Dispatch: scrypt hashes here, everything else to authcore.

    TODO(you):
      - If `stored` starts with `SCRYPT_PREFIX + "$"`, use `verify_scrypt`.
      - Otherwise delegate to `passwords.verify_password`, which already handles
        Argon2id and legacy PBKDF2. Note how little code this needs — that is the
        payoff of a prefix-tagged, self-describing format.
    """
    if stored.startswith(SCRYPT_PREFIX + "$"):
        return verify_scrypt(password, stored)

    return passwords.verify_password(password, stored)
