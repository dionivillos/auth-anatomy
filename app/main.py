from fastapi import FastAPI

app = FastAPI(title="auth-anatomy")


@app.get("/healthz")
def get_healthz() -> dict[str, str]:
    return {"status": "ok"}
