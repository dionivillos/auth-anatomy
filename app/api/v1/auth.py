from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.dependencies import get_current_user
from app.models import User
from app.services.registration import register_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
