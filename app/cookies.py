from fastapi import Response

from app.config import settings
from authcore import sessions as session_rules

SESSION_COOKIE_NAME = "session"


def set_session_cookie(response: Response, raw_token: str) -> None:
    """Attach the session cookie with the security flags.

    - HttpOnly: JavaScript cannot read it, so an XSS bug cannot steal the token.
    - Secure: sent only over HTTPS (configurable off for localhost only).
    - SameSite=Lax: not sent on cross-site subrequests, mitigating CSRF while
      still allowing top-level navigations to the site.
    - Path=/: valid for the whole application.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=int(session_rules.ABSOLUTE_LIFETIME.total_seconds()),
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the session cookie (used on logout)."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
