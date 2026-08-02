from sqlalchemy.orm import Session

from app.repositories.users import UsersRepository
from app.services.sessions import create_session
from authcore import passwords

# A precomputed Argon2id hash used only to spend the same verification time when
# no matching user (or no password) is found, so login timing cannot reveal
# whether an account exists. It is not a real credential.
_DUMMY_HASH = passwords.hash_password("timing-equalizer-not-a-real-password")


def login(
    db: Session,
    *,
    email: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> str | None:
    """Authenticate by password. Return a new session's raw token, or None.

    Failure is indistinguishable across an unknown email, an OAuth-only account
    (no password), and a wrong password: all return None. When there is no real
    hash to check, we still verify against a dummy hash so the response time does
    not reveal whether the account exists (no user enumeration).

    On success the stored hash is transparently upgraded if it is outdated
    (verify-then-rehash), and a brand-new session is created (anti
    session-fixation).
    """
    user = UsersRepository(db).get_by_email(email.strip().lower())

    if user is None or user.password_hash is None:
        # No account, or an OAuth-only one: spend the same time, reveal nothing.
        passwords.verify_password(password, _DUMMY_HASH)
        return None

    stored_hash = user.password_hash
    if not passwords.verify_password(password, stored_hash):
        return None

    if passwords.needs_rehash(stored_hash):
        user.password_hash = passwords.hash_password(password)

    return create_session(db, user_id=user.id, ip=ip, user_agent=user_agent)
