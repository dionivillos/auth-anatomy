from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User

VALID = {
    "email": "alice@example.com",
    "password": "a-perfectly-fine-passphrase",
    "display_name": "Alice",
}


def _count_users(db_session: Session) -> int:
    return db_session.execute(select(func.count()).select_from(User)).scalar_one()


def test_register_creates_user_with_argon2id_hash(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/auth/register", json=VALID)

    assert response.status_code == 201
    assert response.json() == {"status": "ok"}

    user = db_session.execute(select(User)).scalar_one()
    assert user.email == "alice@example.com"
    assert user.display_name == "Alice"
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2id$")
    # The plaintext must never be stored.
    assert VALID["password"] not in user.password_hash


def test_register_lowercases_and_trims_email(client: TestClient, db_session: Session) -> None:
    response = client.post(
        "/api/v1/auth/register", json={**VALID, "email": "  Alice@Example.COM  "}
    )

    assert response.status_code == 201
    user = db_session.execute(select(User)).scalar_one()
    assert user.email == "alice@example.com"


def test_register_duplicate_email_is_neutral(client: TestClient, db_session: Session) -> None:
    first = client.post("/api/v1/auth/register", json=VALID)
    second = client.post("/api/v1/auth/register", json={**VALID, "display_name": "Someone Else"})

    # Identical response: an attacker cannot tell the email was already taken.
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    # And no second row was created.
    assert _count_users(db_session) == 1


def test_register_rejects_common_password(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/auth/register", json={**VALID, "password": "password"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "password_too_common"
    assert _count_users(db_session) == 0


def test_register_rejects_short_password(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/auth/register", json={**VALID, "password": "short"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "password_too_short"
    assert _count_users(db_session) == 0
