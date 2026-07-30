"""Reference solution — Exercise 1 (scrypt dispatch).

One correct approach. The framing mirrors authcore.passwords: a self-describing
string, constant-time comparison, and a prefix-based dispatcher.
"""

import base64
import binascii
import hashlib
import hmac
import secrets

from authcore import passwords

SCRYPT_PREFIX = "scrypt"

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_SALT_BYTES = 16
_SCRYPT_DKLEN = 32


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_scrypt(password: str) -> str:
    salt = secrets.token_bytes(_SCRYPT_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"{SCRYPT_PREFIX}${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64e(salt)}${_b64e(derived)}"


def verify_scrypt(password: str, stored: str) -> bool:
    fields = stored.split("$")
    if len(fields) != 6 or fields[0] != SCRYPT_PREFIX:
        raise ValueError("not a well-formed scrypt hash")
    _, n_raw, r_raw, p_raw, salt_b64, hash_b64 = fields
    try:
        n, r, p = int(n_raw), int(r_raw), int(p_raw)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("corrupt scrypt hash") from exc

    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected)
    )
    return hmac.compare_digest(derived, expected)


def verify_any(password: str, stored: str) -> bool:
    if stored.startswith(SCRYPT_PREFIX + "$"):
        return verify_scrypt(password, stored)
    return passwords.verify_password(password, stored)
