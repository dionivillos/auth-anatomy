# Architecture

auth-anatomy is layered so that each piece has one responsibility and the
security-critical logic can be reasoned about and tested in isolation.

## The layers

```
            HTTP request
                │
        ┌───────▼────────┐   app/api/v1/ (JSON), app/web/ (HTML)
        │   boundary     │   routers, request/response schemas, dependencies
        └───────┬────────┘   NO business logic
                │
        ┌───────▼────────┐   app/services/
        │    services    │   use-case orchestration; OWNS the transaction
        └───────┬────────┘
                │
        ┌───────▼────────┐   app/repositories/
        │  repositories  │   data access for one aggregate; NEVER commits
        └───────┬────────┘
                │
        ┌───────▼────────┐   app/models.py (SQLAlchemy ORM) + Alembic migrations
        │   persistence  │
        └────────────────┘

        ┌────────────────┐   authcore/
        │    authcore    │   PURE domain logic: hashing, tokens, policy, session
        │   (pure core)  │   expiry rules. No FastAPI, no SQLAlchemy, no I/O.
        └────────────────┘   Called by services with plain values.
```

## The dependency rule

`authcore` never imports from `app`, FastAPI, or SQLAlchemy. It takes plain
values (strings, datetimes, bytes) and returns plain values or dataclasses. The
arrow of dependency only ever points **inward**: `app` depends on `authcore`,
never the reverse.

Why: the domain logic whose bugs are security bugs (password hashing, token
generation, JWT validation, TOTP, session expiry) is kept free of frameworks and
I/O, so it runs in milliseconds under test — including the attack paths — with no
database or HTTP fixtures. See [`authcore/`](../../authcore/).

## Component responsibilities

| Layer | Location | Responsibility | Rule |
|---|---|---|---|
| Pure core | `authcore/` | Algorithms & rules: `passwords`, `tokens`, `policy`, `sessions` (expiry) | No I/O, no framework |
| Models | `app/models.py` | ORM tables; timezone-aware UTC timestamps | Schema lives in Alembic |
| Repositories | `app/repositories/` | Data access per aggregate (`users`, `sessions`) | Never commit |
| Services | `app/services/` | Orchestrate authcore + repos; email; etc. | Own the transaction |
| Boundary (API) | `app/api/v1/` | JSON routers + Pydantic schemas | No business logic |
| Boundary (web) | `app/web/` | HTML routers + Jinja templates | No business logic |
| Cross-cutting | `app/cookies.py`, `app/dependencies.py`, `app/errors.py`, `app/config.py`, `app/db.py` | Cookies, DI, error shape, settings, engine/session | — |

## Transactions

Services own transaction boundaries; repositories never call `commit()`. A
repository `add`s and `flush`es (so a constraint violation surfaces as an
`IntegrityError` *within* the transaction), and the calling service decides
whether to `commit()` or `rollback()`. This keeps a use case atomic in one place
— see, for example, the neutral-duplicate handling in
[`app/services/registration.py`](../../app/services/registration.py).

The FastAPI dependency [`get_session`](../../app/db.py) yields a session per
request and always closes it.

## Error handling

The JSON API uses one uniform shape:

```json
{ "error": { "code": "stable_machine_slug", "message": "human readable" } }
```

Domain errors carry a `code` + `message` and are turned into that shape by
app-level exception handlers in [`app/main.py`](../../app/main.py):

- `authcore.exceptions.PasswordPolicyError` → HTTP 400 with its code.
- `app.errors.ApiError` (status + code + message) → its status with its code; used
  for e.g. the `not_authenticated` 401 from `get_current_user`.

## Request lifecycle (authenticated request)

An authenticated call to `GET /api/v1/auth/me`:

1. FastAPI resolves the route's dependencies. `get_current_user`
   ([`app/dependencies.py`](../../app/dependencies.py)) runs first.
2. It reads the `session` cookie and calls `validate_session`
   ([`app/services/sessions.py`](../../app/services/sessions.py)).
3. The service hashes the token, looks up the session row, applies the pure
   expiry rules from [`authcore/sessions.py`](../../authcore/sessions.py), slides
   the idle window, and returns the `User` (or `None`).
4. On `None`, `get_current_user` raises `ApiError(401, "not_authenticated", …)`,
   which the handler renders as the uniform error shape. Otherwise the route
   handler receives the `User` and returns its data.

The full session flow is walked through in [How a session works](sessions.md).

## Configuration and secrets

All configuration comes from environment variables via `pydantic-settings`
([`app/config.py`](../../app/config.py)); secrets are never committed. The
database URL drives the engine ([`app/db.py`](../../app/db.py)); it defaults to a
local SQLite file and switches to PostgreSQL from module 04.

## Testing

- `tests/authcore/` — pure unit tests (including RFC vectors and attack paths).
- `tests/api/`, `tests/web/`, `tests/app/` — integration tests using an
  in-memory SQLite database wired in through a `get_session` dependency override
  ([`tests/conftest.py`](../../tests/conftest.py)).
