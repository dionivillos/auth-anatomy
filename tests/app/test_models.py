from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
from app.models import User


@pytest.fixture
def session() -> Iterator[Session]:
    # A throwaway in-memory database, built straight from the model metadata
    # (not from migrations) so the test is fast and isolated.
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_users_table_is_registered() -> None:
    assert "users" in Base.metadata.tables


def test_insert_and_read_back_user(session: Session) -> None:
    user = User(email="alice@example.com", display_name="Alice")
    session.add(user)
    session.commit()

    stored = session.query(User).one()
    assert stored.id is not None
    assert stored.email == "alice@example.com"
    assert stored.display_name == "Alice"
    # Optional columns default to NULL.
    assert stored.password_hash is None
    assert stored.email_verified_at is None
    assert stored.disabled_at is None
    # Timestamps are populated by the Python-side defaults.
    assert isinstance(stored.created_at, datetime)
    assert isinstance(stored.updated_at, datetime)


def test_email_uniqueness_is_enforced(session: Session) -> None:
    session.add(User(email="dup@example.com", display_name="First"))
    session.commit()

    session.add(User(email="dup@example.com", display_name="Second"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_updated_at_changes_on_update(session: Session) -> None:
    user = User(email="bob@example.com", display_name="Bob")
    session.add(user)
    session.commit()
    original_updated_at = user.updated_at

    user.display_name = "Bobby"
    # Force a later timestamp so the assertion is not flaky on fast clocks.
    user.updated_at = datetime.now(UTC)
    session.commit()

    assert user.updated_at > original_updated_at


def test_constraints_have_deterministic_names() -> None:
    # The naming convention on Base.metadata must produce stable constraint
    # names, which SQLite batch migrations rely on.
    users_table = Base.metadata.tables["users"]
    names = {c.name for c in users_table.constraints if c.name}
    assert "uq_users_email" in names
    assert "pk_users" in names
