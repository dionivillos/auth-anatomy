from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.cookies import SESSION_COOKIE_NAME, clear_session_cookie, set_session_cookie
from app.db import get_session
from app.dependencies import get_current_user
from app.errors import ApiError
from app.models import User
from app.services.login import login
from app.services.registration import register_user
from app.services.sessions import revoke_all_sessions, revoke_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class StatusResponse(BaseModel):
    status: str


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client is not None else None


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1)
    display_name: str = Field(min_length=1, max_length=200)


class RegisterResponse(BaseModel):
    status: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def post_register(
    payload: RegisterRequest,
    session: Annotated[Session, Depends(get_session)],
) -> RegisterResponse:
    # The response is intentionally the same for a new account and a duplicate
    # email: the service handles the collision silently, so this endpoint never
    # reveals whether the address was already registered.
    register_user(
        session,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    return RegisterResponse(status="ok")


class MeResponse(BaseModel):
    id: int
    email: str
    display_name: str


@router.get("/me")
def get_me(user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse(id=user.id, email=user.email, display_name=user.display_name)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1)


@router.post("/login")
def post_login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_session)],
) -> StatusResponse:
    raw_token = login(
        db,
        email=payload.email,
        password=payload.password,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    # A failed login is a single generic error: it never says whether the email
    # exists or the password was wrong.
    if raw_token is None:
        raise ApiError(401, "invalid_credentials", "Invalid email or password.")
    set_session_cookie(response, raw_token)
    return StatusResponse(status="ok")


@router.post("/logout")
def post_logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_session)],
) -> StatusResponse:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is not None:
        revoke_session(db, token)
    clear_session_cookie(response)
    return StatusResponse(status="ok")


@router.post("/logout-all")
def post_logout_all(
    user: Annotated[User, Depends(get_current_user)],
    response: Response,
    db: Annotated[Session, Depends(get_session)],
) -> StatusResponse:
    revoke_all_sessions(db, user.id)
    clear_session_cookie(response)
    return StatusResponse(status="ok")
