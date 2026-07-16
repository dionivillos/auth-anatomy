# auth-anatomy

A complete authentication system built from scratch in Python — password hashing, sessions,
email flows, JWT, TOTP, OAuth 2.0, and WebAuthn passkeys, each implemented and explained rather
than pulled from an auth library.

This is a learning project and a portfolio piece, not a library meant for production use.
See [CLAUDE.md](CLAUDE.md) for the full technical spec and task plan.

## Curriculum

| Module | Topic | Status |
|---|---|---|
| 00 | Project setup | Not started |
| 01 | Passwords & registration | Not started |
| 02 | Sessions from scratch | Not started |
| 03 | Email flows | Not started |
| 04 | Hardening & PostgreSQL | Not started |
| 05 | JWT from scratch | Not started |
| 06 | TOTP from scratch | Not started |
| 07 | OAuth 2.0 client | Not started |
| 08 | Passkeys & capstone | Not started |

Each module ships tested code, a lesson document in `docs/lessons/`, and a git tag
(`v0.N-module-NN`). Checking out a tag gives you the working system at that point in the curriculum.

## Quickstart

```bash
uv sync
cp .env.example .env
docker compose up -d       # Mailpit (M3+) and PostgreSQL (M4+)
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

Swagger UI: http://localhost:8000/docs
Mailpit UI: http://localhost:8025

## Development

```bash
uv run pytest                              # tests
uv run pytest --cov=authcore --cov=app     # tests with coverage
uv run ruff check . && uv run ruff format . # lint + format
uv run mypy .                              # type check
```

## Future work

Ideas outside the current curriculum scope go here instead of into the code:

- Second OAuth provider (Google) to prove the abstraction
- Magic links via email
- Async SQLAlchemy
- Deploying a live demo

## License

MIT — see [LICENSE](LICENSE).
