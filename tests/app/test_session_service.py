from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserSession
from app.services import sessions as session_service
from authcore import sessions as rules
from authcore import tokens

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@pytest.fixture
def user(db_session: Session) -> User:
    user = User(email="a@example.com", display_name="A", password_hash="x")
    db_session.add(user)
    db_session.commit()
    return user


def test_create_session_returns_raw_token_and_stores_only_hash(
    db_session: Session, user: User
) -> None:
    raw = session_service.create_session(db_session, user_id=user.id)

    assert len(raw) == 32
    row = db_session.execute(select(UserSession)).scalar_one()
    assert row.token_hash == tokens.sha256_hex(raw)
    assert row.token_hash != raw  # the raw token is never stored


def test_validate_returns_user_for_a_valid_token(db_session: Session, user: User) -> None:
    raw = session_service.create_session(db_session, user_id=user.id)

    result = session_service.validate_session(db_session, raw)

    assert result is not None
    assert result.id == user.id


def test_validate_unknown_token_returns_none(db_session: Session, user: User) -> None:
    assert session_service.validate_session(db_session, "NOSUCHTOKEN") is None


def test_validate_slides_the_idle_window(db_session: Session, user: User) -> None:
    raw = session_service.create_session(db_session, user_id=user.id, now=NOW)
    later = NOW + timedelta(days=1)

    session_service.validate_session(db_session, raw, now=later)

    row = db_session.execute(select(UserSession)).scalar_one()
    assert _utc(row.last_used_at) == later


def test_session_past_absolute_deadline_is_rejected_and_deleted(
    db_session: Session, user: User
) -> None:
    raw = session_service.create_session(db_session, user_id=user.id, now=NOW)
    way_later = NOW + rules.ABSOLUTE_LIFETIME + timedelta(days=1)

    assert session_service.validate_session(db_session, raw, now=way_later) is None
    assert db_session.execute(select(UserSession)).first() is None  # cleaned up


def test_idle_session_is_rejected(db_session: Session, user: User) -> None:
    raw = session_service.create_session(db_session, user_id=user.id, now=NOW)
    idle_later = NOW + rules.IDLE_TIMEOUT + timedelta(seconds=1)

    assert session_service.validate_session(db_session, raw, now=idle_later) is None


def test_revoked_session_is_rejected(db_session: Session, user: User) -> None:
    raw = session_service.create_session(db_session, user_id=user.id)

    session_service.revoke_session(db_session, raw)

    assert session_service.validate_session(db_session, raw) is None


def test_revoke_all_sessions_invalidates_every_session(db_session: Session, user: User) -> None:
    raw1 = session_service.create_session(db_session, user_id=user.id)
    raw2 = session_service.create_session(db_session, user_id=user.id)

    session_service.revoke_all_sessions(db_session, user.id)

    assert session_service.validate_session(db_session, raw1) is None
    assert session_service.validate_session(db_session, raw2) is None
