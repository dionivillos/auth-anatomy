from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.cookies import SESSION_COOKIE_NAME
from app.db import get_session
from app.errors import ApiError
from app.models import User
from app.services.sessions import validate_session


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_session)],
) -> User:
    """FastAPI dependency resolving to the authenticated user, or a 401.

    The 401 is identical whether the cookie is absent or invalid (unknown,
    expired, or revoked session) — we never reveal which.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise ApiError(401, "not_authenticated", "Authentication required.")
    user = validate_session(db, token)
    if user is None:
        raise ApiError(401, "not_authenticated", "Authentication required.")
    return user
