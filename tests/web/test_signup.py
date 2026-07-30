from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User

FORM = {
    "email": "bob@example.com",
    "display_name": "Bob",
    "password": "another-fine-passphrase",
}


def test_get_signup_renders_form(client: TestClient) -> None:
    response = client.get("/signup")

    assert response.status_code == 200
    assert "<form" in response.text
    assert 'name="email"' in response.text


def test_post_signup_creates_user(client: TestClient, db_session: Session) -> None:
    response = client.post("/signup", data=FORM)

    assert response.status_code == 200
    assert "created" in response.text.lower()

    user = db_session.execute(select(User)).scalar_one()
    assert user.email == "bob@example.com"
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2id$")


def test_post_signup_shows_policy_error(client: TestClient, db_session: Session) -> None:
    response = client.post("/signup", data={**FORM, "password": "password"})

    assert response.status_code == 200
    assert "too common" in response.text.lower()
    # The form is shown again so the user can retry.
    assert "<form" in response.text
    assert db_session.execute(select(User)).first() is None
