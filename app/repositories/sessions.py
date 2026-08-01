from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import UserSession


class SessionsRepository:
    """Data access for the ``sessions`` aggregate. Never commits — the service
    owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        token_hash: str,
        user_id: int,
        created_at: datetime,
        expires_at: datetime,
        last_used_at: datetime,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        row = UserSession(
            token_hash=token_hash,
            user_id=user_id,
            created_at=created_at,
            expires_at=expires_at,
            last_used_at=last_used_at,
            ip=ip,
            user_agent=user_agent,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        return self._session.execute(
            select(UserSession).where(UserSession.token_hash == token_hash)
        ).scalar_one_or_none()

    def delete(self, row: UserSession) -> None:
        self._session.delete(row)

    def delete_all_for_user(self, user_id: int) -> None:
        self._session.execute(delete(UserSession).where(UserSession.user_id == user_id))
