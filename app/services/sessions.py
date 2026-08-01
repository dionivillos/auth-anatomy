from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import User
from app.repositories.sessions import SessionsRepository
from authcore import sessions as session_rules
from authcore import tokens


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    """Attach UTC to a naive datetime read from SQLite (a no-op on PostgreSQL,
    which returns timezone-aware values). The authcore rules require aware UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def create_session(
    db: Session,
    *,
    user_id: int,
    ip: str | None = None,
    user_agent: str | None = None,
    now: datetime | None = None,
) -> str:
    """Create a session and return the raw token (shown to the client once).

    Only the token's SHA-256 hash is stored. `now` is injectable for testing.
    """
    now = now or _now()
    raw_token = tokens.generate()
    SessionsRepository(db).create(
        token_hash=tokens.sha256_hex(raw_token),
        user_id=user_id,
        created_at=now,
        expires_at=session_rules.absolute_expiry(now),
        last_used_at=now,
        ip=ip,
        user_agent=user_agent,
    )
    db.commit()
    return raw_token


def validate_session(db: Session, raw_token: str, *, now: datetime | None = None) -> User | None:
    """Return the session's user if the token is valid, else None.

    Expired sessions are deleted. A valid session has its idle window slid
    forward (last_used_at = now).
    """
    now = now or _now()
    repo = SessionsRepository(db)
    row = repo.get_by_token_hash(tokens.sha256_hex(raw_token))
    if row is None:
        return None

    if session_rules.is_expired(
        now, expires_at=_as_utc(row.expires_at), last_used_at=_as_utc(row.last_used_at)
    ):
        repo.delete(row)
        db.commit()
        return None

    row.last_used_at = now  # slide the idle window forward
    db.commit()
    return db.get(User, row.user_id)


def revoke_session(db: Session, raw_token: str) -> None:
    """Revoke the session identified by `raw_token` (logout). No-op if absent."""
    repo = SessionsRepository(db)
    row = repo.get_by_token_hash(tokens.sha256_hex(raw_token))
    if row is not None:
        repo.delete(row)
        db.commit()


def revoke_all_sessions(db: Session, user_id: int) -> None:
    """Revoke every session for a user (logout-all)."""
    SessionsRepository(db).delete_all_for_user(user_id)
    db.commit()
