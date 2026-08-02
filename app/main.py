from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import auth as api_auth
from app.errors import ApiError
from app.web import login as web_login
from app.web import signup as web_signup
from authcore.exceptions import PasswordPolicyError

app = FastAPI(title="auth-anatomy")


@app.get("/healthz")
def get_healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(PasswordPolicyError)
async def handle_password_policy_error(request: Request, exc: Exception) -> JSONResponse:
    # Narrowed for the type checker; FastAPI only routes PasswordPolicyError here.
    assert isinstance(exc, PasswordPolicyError)
    return JSONResponse(
        status_code=400,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


app.include_router(api_auth.router)
app.include_router(web_signup.router)
app.include_router(web_login.router)
