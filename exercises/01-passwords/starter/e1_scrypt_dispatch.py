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
    raise NotImplementedError


def verify_scrypt(password: str, stored: str) -> bool:
    """Verify a scrypt hash, reading n/r/p and the salt from `stored`.

    TODO(you):
      1. Split into exactly 6 fields; the first must equal SCRYPT_PREFIX.
      2. Parse n, r, p as ints and base64-decode the salt and expected hash.
      3. Re-derive with the parsed parameters and compare with
         `hmac.compare_digest` (constant time).
      4. Raise ValueError if `stored` is not a well-formed scrypt hash.
    """
    raise NotImplementedError


def verify_any(password: str, stored: str) -> bool:
    """Dispatch: scrypt hashes here, everything else to authcore.

    TODO(you):
      - If `stored` starts with `SCRYPT_PREFIX + "$"`, use `verify_scrypt`.
      - Otherwise delegate to `passwords.verify_password`, which already handles
        Argon2id and legacy PBKDF2. Note how little code this needs — that is the
        payoff of a prefix-tagged, self-describing format.
    """
    raise NotImplementedError
