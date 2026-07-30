from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_session
from app.services.registration import register_user
from authcore.exceptions import PasswordPolicyError

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/signup", response_class=HTMLResponse)
def get_signup(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="signup.html", context={})


@router.post("/signup", response_class=HTMLResponse)
def post_signup(
    request: Request,
    email: Annotated[str, Form()],
    display_name: Annotated[str, Form()],
    password: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    try:
        register_user(session, email=email, password=password, display_name=display_name)
    except PasswordPolicyError as exc:
        # Re-render the form with the reason, preserving the non-secret fields.
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"error": exc.message, "email": email, "display_name": display_name},
        )
    return templates.TemplateResponse(
        request=request, name="signup.html", context={"success": True}
    )
