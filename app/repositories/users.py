from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UsersRepository:
    """Data access for the ``users`` aggregate.

    Repositories never commit — the calling service owns the transaction. A
    ``flush`` is used to push the INSERT to the database so a unique-constraint
    violation surfaces as an ``IntegrityError`` inside the service's transaction,
    without ending it.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        return self._session.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def create(self, *, email: str, password_hash: str | None, display_name: str) -> User:
        user = User(email=email, password_hash=password_hash, display_name=display_name)
        self._session.add(user)
        self._session.flush()
        return user
