from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cookies import SESSION_COOKIE_NAME
from app.models import User
from app.services import sessions as session_service
from authcore import passwords

PASSWORD = "a-correct-horse-passphrase"


def _make_user(db_session: Session, *, email: str = "user@example.com") -> User:
    user = User(email=email, display_name="U", password_hash=passwords.hash_password(PASSWORD))
    db_session.add(user)
    db_session.commit()
    return user


def test_login_success_sets_cookie_and_authenticates(
    client: TestClient, db_session: Session
) -> None:
    _make_user(db_session)

    response = client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert client.cookies.get(SESSION_COOKIE_NAME) is not None
    # The freshly set cookie authenticates a follow-up request.
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


def test_login_wrong_password_is_401(client: TestClient, db_session: Session) -> None:
    _make_user(db_session)

    response = client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "WRONGPASS"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_unknown_email_is_indistinguishable_from_wrong_password(
    client: TestClient, db_session: Session
) -> None:
    _make_user(db_session)

    unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "WRONGPASS"}
    )
    wrong = client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "WRONGPASS"}
    )

    # Identical response: registration/login cannot be used to enumerate accounts.
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_login_issues_a_new_session_each_time(client: TestClient, db_session: Session) -> None:
    _make_user(db_session)
    # An attacker-planted cookie must not be adopted (anti session-fixation).
    client.cookies.set(SESSION_COOKIE_NAME, "ATTACKER-PLANTED-VALUE")

    # Read the issued token from each response's Set-Cookie, not the merged jar.
    first = client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": PASSWORD}
    )
    token1 = first.cookies.get(SESSION_COOKIE_NAME)
    assert token1 is not None
    assert token1 != "ATTACKER-PLANTED-VALUE"

    second = client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": PASSWORD}
    )
    token2 = second.cookies.get(SESSION_COOKIE_NAME)
    assert token2 is not None
    assert token2 != token1  # a new session id on every login


def test_login_upgrades_a_legacy_pbkdf2_hash(client: TestClient, db_session: Session) -> None:
    user = User(
        email="legacy@example.com",
        display_name="L",
        password_hash=passwords._hash_pbkdf2(PASSWORD),
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login", json={"email": "legacy@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    db_session.refresh(user)
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2id$")


def test_logout_revokes_the_current_session(client: TestClient, db_session: Session) -> None:
    _make_user(db_session)
    client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": PASSWORD})
    assert client.get("/api/v1/auth/me").status_code == 200

    client.post("/api/v1/auth/logout")

    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_all_revokes_every_session(client: TestClient, db_session: Session) -> None:
    user = _make_user(db_session)
    raw1 = session_service.create_session(db_session, user_id=user.id)
    raw2 = session_service.create_session(db_session, user_id=user.id)

    client.cookies.set(SESSION_COOKIE_NAME, raw1)
    assert client.post("/api/v1/auth/logout-all").status_code == 200

    for raw in (raw1, raw2):
        client.cookies.set(SESSION_COOKIE_NAME, raw)
        assert client.get("/api/v1/auth/me").status_code == 401
