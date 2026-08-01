from fastapi import Response

from app.cookies import SESSION_COOKIE_NAME, clear_session_cookie, set_session_cookie


def test_set_session_cookie_carries_the_security_flags() -> None:
    response = Response()

    set_session_cookie(response, "TOKENVALUE")

    header = response.headers["set-cookie"]
    lower = header.lower()
    assert f"{SESSION_COOKIE_NAME}=TOKENVALUE" in header
    assert "httponly" in lower
    assert "samesite=lax" in lower
    assert "path=/" in lower
    assert "max-age=" in lower


def test_set_session_cookie_omits_secure_when_disabled() -> None:
    # secure_cookies defaults to False for local development.
    response = Response()

    set_session_cookie(response, "TOKENVALUE")

    assert "secure" not in response.headers["set-cookie"].lower()


def test_clear_session_cookie_expires_it() -> None:
    response = Response()

    clear_session_cookie(response)

    header = response.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE_NAME}=" in header
    assert "max-age=0" in header or "expires=thu, 01 jan 1970" in header
