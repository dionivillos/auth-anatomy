from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.cookies import set_session_cookie
from app.db import get_session
from app.services.login import login

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def get_login(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="login.html", context={})


@router.post("/login", response_class=HTMLResponse)
def post_login(
    request: Request,
    response: Response,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    raw_token = login(db, email=email, password=password)
    if raw_token is None:
        # Single generic error — never reveals whether the email exists.
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid email or password.", "email": email},
        )
    html = templates.TemplateResponse(request=request, name="login.html", context={"success": True})
    set_session_cookie(html, raw_token)
    return html
