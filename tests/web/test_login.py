from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cookies import SESSION_COOKIE_NAME
from app.models import User
from authcore import passwords

PASSWORD = "a-correct-horse-passphrase"


def _make_user(db_session: Session) -> User:
    user = User(
        email="web@example.com", display_name="W", password_hash=passwords.hash_password(PASSWORD)
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_get_login_renders_form(client: TestClient) -> None:
    response = client.get("/login")

    assert response.status_code == 200
    assert "<form" in response.text
    assert 'name="password"' in response.text


def test_post_login_success_sets_cookie(client: TestClient, db_session: Session) -> None:
    _make_user(db_session)

    response = client.post("/login", data={"email": "web@example.com", "password": PASSWORD})

    assert response.status_code == 200
    assert "logged in" in response.text.lower()
    assert client.cookies.get(SESSION_COOKIE_NAME) is not None


def test_post_login_wrong_shows_generic_error(client: TestClient, db_session: Session) -> None:
    _make_user(db_session)

    response = client.post("/login", data={"email": "web@example.com", "password": "WRONGPASS"})

    assert response.status_code == 200
    assert "invalid email or password" in response.text.lower()
    assert "<form" in response.text
