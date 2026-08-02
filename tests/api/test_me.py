from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cookies import SESSION_COOKIE_NAME
from app.models import User
from app.services import sessions as session_service


def _make_user(db_session: Session) -> User:
    user = User(email="me@example.com", display_name="Me", password_hash="x")
    db_session.add(user)
    db_session.commit()
    return user


def test_me_returns_the_current_user_with_a_valid_cookie(
    client: TestClient, db_session: Session
) -> None:
    user = _make_user(db_session)
    raw_token = session_service.create_session(db_session, user_id=user.id)
    client.cookies.set(SESSION_COOKIE_NAME, raw_token)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user.id
    assert body["email"] == "me@example.com"
    assert body["display_name"] == "Me"


def test_me_without_a_cookie_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_with_an_invalid_cookie_is_401(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, "NOTAREALTOKEN")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
