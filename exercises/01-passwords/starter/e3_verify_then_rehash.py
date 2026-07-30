"""Exercise 3 — A pure verify-then-rehash orchestrator.

Difficulty: ★★★

The module described the verify-then-rehash pattern in prose and split it across
`verify_password` / `needs_rehash`. Package it as a single pure function the
service layer can call at login, returning both the outcome and — when relevant —
the upgraded hash to persist.

Design it as pure logic (no database, no I/O): it takes the stored hash and the
submitted password, and returns an `AuthResult`. The caller decides what to do
with `new_hash` (write it back, or ignore it).

Complete `AuthResult` and `authenticate` so `test_e3_verify_then_rehash.py`
passes. Reference solution: `solutions/e3_verify_then_rehash.py`.
"""

from dataclasses import dataclass

from authcore import passwords


@dataclass(frozen=True)
class AuthResult:
    """Outcome of a password check.

    Attributes:
        ok: whether the password matched.
        new_hash: an upgraded hash to persist, or None. Set only when `ok` is True
            and the stored hash was below the current standard.
    """

    ok: bool
    new_hash: str | None = None


def authenticate(stored_hash: str, password: str) -> AuthResult:
    """Verify `password` against `stored_hash` and decide on an upgrade.

    TODO(you):
      1. Verify with `passwords.verify_password(password, stored_hash)`.
      2. On failure, return AuthResult(ok=False).
      3. On success, check `passwords.needs_rehash(stored_hash)`:
           - if it needs a rehash, return AuthResult(ok=True,
             new_hash=passwords.hash_password(password)) — the plaintext is in
             hand right now, the only moment it is available.
           - otherwise return AuthResult(ok=True) with no new_hash.
    """
    raise NotImplementedError
