"""Reference solution — Exercise 3 (verify-then-rehash orchestrator)."""

from dataclasses import dataclass

from authcore import passwords


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    new_hash: str | None = None


def authenticate(stored_hash: str, password: str) -> AuthResult:
    if not passwords.verify_password(password, stored_hash):
        return AuthResult(ok=False)

    if passwords.needs_rehash(stored_hash):
        return AuthResult(ok=True, new_hash=passwords.hash_password(password))

    return AuthResult(ok=True)
