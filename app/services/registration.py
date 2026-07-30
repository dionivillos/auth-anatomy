from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.users import UsersRepository
from authcore import passwords, policy


def register_user(session: Session, *, email: str, password: str, display_name: str) -> None:
    """Register a new account. Returns None; neutral on duplicate email.

    The response is identical whether or not the email already existed, so an
    attacker cannot use registration to enumerate accounts.

    The password policy is validated first and its ``PasswordPolicyError`` is
    allowed to propagate to the boundary layer. The duplicate-email case is
    handled by attempting the insert and catching the ``IntegrityError`` raised
    by the UNIQUE constraint, rather than a prior ``get_by_email`` check: two
    concurrent requests could both pass such a check and then both insert, so
    only the database constraint serialises them safely (avoiding the TOCTOU
    race). The winner commits; the loser rolls back and returns neutrally.
    """
    normalized_email = email.strip().lower()
    policy.check_password(password)
    password_hash = passwords.hash_password(password)
    try:
        UsersRepository(session).create(
            email=normalized_email,
            password_hash=password_hash,
            display_name=display_name,
        )
        session.commit()
    except IntegrityError:
        session.rollback()
