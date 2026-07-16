# CLAUDE.md

## Project

**auth-anatomy** is a learning-first authentication system built from scratch in Python. It implements password auth, server-side sessions, email flows, hardening, JWT, TOTP, OAuth 2.0 (client) and WebAuthn passkeys, organized as a 9-module curriculum (00-08). The repository is both a working system and teaching material: every module ships tested code, a lesson document in `docs/lessons/`, and a git tag.

**Working mode:** the human is the primary learner and developer. Follow the task plan below strictly; do not reorder modules, do not add features outside the plan, and do not substitute the hand-rolled implementations with libraries. When generating code, prefer explaining the security reasoning in the process. The human decides how much code to delegate to you per task.

## Stack

- Python 3.12+ (managed by uv)
- FastAPI (latest stable, pinned in pyproject.toml at task 0.1)
- Jinja2 templates for HTML pages
- SQLAlchemy 2.0 (sync mode) + Alembic migrations
- SQLite (modules 0-3), PostgreSQL 16 via Docker Compose (module 4 onward)
- argon2-cffi (Argon2id password hashing)
- cryptography (Fernet, encryption-at-rest for TOTP secrets only)
- segno (QR codes for TOTP provisioning)
- httpx (OAuth HTTP calls and test client)
- webauthn (py_webauthn, module 8 only)
- pydantic-settings + .env for configuration
- Mailpit via Docker Compose (local SMTP capture)
- Tooling: uv, ruff (lint + format), mypy --strict, pytest + coverage, pre-commit, GitHub Actions

**Deliberately NOT used (hand-rolled instead):** PyJWT / python-jose (JWT is implemented in `authcore/jwt.py`), pyotp (TOTP in `authcore/totp.py`), authlib (OAuth flow in `authcore/oauth.py`), passlib (dispatch logic in `authcore/passwords.py`).

## Repository structure

```
auth-anatomy/
├── pyproject.toml           # deps, ruff/mypy/pytest config
├── uv.lock
├── README.md                # curriculum index, quickstart
├── CLAUDE.md                # this file
├── .env.example
├── docker-compose.yml       # mailpit (M3+), postgres (M4+)
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml # lint, typecheck, tests, coverage
├── alembic/                 # migrations (single source of truth for schema)
├── authcore/                # PURE domain logic: no FastAPI, no SQLAlchemy, no I/O
│   ├── passwords.py         # PBKDF2 (educational) + Argon2id, PHC prefix dispatch, needs_rehash
│   ├── policy.py            # password policy (min 8, max 128, no composition rules)
│   ├── tokens.py            # CSPRNG token generation (base32), SHA-256 hashing, constant-time compare
│   ├── sessions.py          # session expiry/validation rules (no persistence)
│   ├── jwt.py               # base64url + HS256 sign/verify + claims validation (M5)
│   ├── totp.py              # HOTP RFC 4226 + TOTP RFC 6238 (M6)
│   ├── oauth.py             # authorization URL, state, PKCE, code exchange (HTTP client injected) (M7)
│   ├── webauthn.py          # thin wrapper over py_webauthn (M8)
│   ├── ratelimit.py         # window/lockout algorithm (M4)
│   └── exceptions.py
├── app/
│   ├── main.py              # FastAPI app factory, router registration
│   ├── config.py            # pydantic-settings
│   ├── db.py                # engine, session factory
│   ├── models.py            # SQLAlchemy ORM models
│   ├── repositories/        # one repo per aggregate (users, sessions, tokens, ...)
│   ├── services/            # use-case orchestration (authcore + repos + emails); transactions live here
│   ├── api/v1/              # JSON routers, Pydantic schemas; uniform error shape {error: {code, message}}
│   ├── web/                 # HTML routers (signup, login, verify, reset, account, security)
│   ├── templates/           # Jinja2
│   ├── static/              # minimal CSS + WebAuthn JS (M8)
│   └── emails/              # SMTP sender + plain-text templates
├── tests/
│   ├── authcore/            # pure unit tests, incl. RFC test vectors
│   ├── api/                 # httpx TestClient integration tests
│   └── web/
└── docs/
    ├── lessons/             # 00-project-setup.md ... 08-passkeys-and-sudo.md
    └── architecture.md      # written in M8
```

## Code conventions

- Everything in English: code, comments, docstrings, commits, docs.
- ruff for linting and formatting (line length 100). mypy --strict must pass; `Any` is forbidden except at documented third-party boundaries.
- Naming: snake_case modules/functions, PascalCase classes, UPPER_SNAKE constants. Route functions named `<verb>_<resource>` (e.g. `post_login`).
- `authcore` must never import from `app`, FastAPI, or SQLAlchemy. It receives plain values and returns plain values/dataclasses. Enforce with an import-linter contract or a dedicated test.
- Services own transactions; repositories never commit. Routers contain no business logic.
- All timestamps timezone-aware UTC. All randomness from `secrets` (never `random`).
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), scoped by module when useful (`feat(m2): ...`).
- Every module ends with a git tag `v0.<N>-module-0<N>`; final tag `v1.0`.

## Commands

- Install dependencies: `uv sync`
- Run dev server: `uv run fastapi dev app/main.py` (Swagger UI at http://localhost:8000/docs)
- Run tests: `uv run pytest` (with coverage: `uv run pytest --cov=authcore --cov=app`)
- Lint + format: `uv run ruff check .` / `uv run ruff format .`
- Type check: `uv run mypy .`
- Migrations: `uv run alembic revision --autogenerate -m "..."` / `uv run alembic upgrade head`
- Local services: `docker compose up -d` (Mailpit UI at http://localhost:8025)
- Maintenance: `uv run python -m app.cli purge-expired` (sessions, one-time tokens, challenges, throttles)

## Data model

Conventions: integer autoincrement PK `id` unless stated; UTC timestamps; FKs `ON DELETE CASCADE` unless stated; tokens are NEVER stored raw, only their SHA-256 hash.

- **users**: id, email (TEXT UNIQUE NOT NULL, lowercased), email_verified_at (NULL), password_hash (TEXT NULL - null for OAuth-only accounts, PHC format), display_name (NOT NULL), created_at, updated_at, disabled_at (NULL)
- **sessions**: id, token_hash (UNIQUE NOT NULL), user_id FK, created_at, expires_at, last_used_at (sliding expiry), sudo_until (NULL, M8), ip (NULL), user_agent (NULL)
- **one_time_tokens**: id, purpose CHECK IN ('email_verification','password_reset'), token_hash UNIQUE, user_id FK, email (NULL), created_at, expires_at. Single-use: consume = validate + delete in one transaction.
- **refresh_tokens** (M5): id, token_hash UNIQUE, user_id FK, family_id (NOT NULL), issued_at, expires_at, revoked_at (NULL), replaced_by_id (NULL, self-FK)
- **totp_credentials** (M6): user_id PK/FK (one per user), secret_encrypted (BLOB, Fernet), confirmed_at (NULL until first valid code), last_used_step (BIGINT NULL, anti-replay), created_at
- **recovery_codes** (M6): id, user_id FK, code_hash, created_at, used_at (NULL)
- **login_challenges** (M6): id, token_hash UNIQUE, user_id FK, kind CHECK IN ('totp'), created_at, expires_at (TTL 5 min)
- **oauth_accounts** (M7): id, user_id FK, provider, provider_user_id, email (NULL), created_at, UNIQUE(provider, provider_user_id)
- **webauthn_credentials** (M8): id, user_id FK, credential_id (TEXT UNIQUE, base64url), public_key (BLOB), sign_count (INT DEFAULT 0), transports (NULL), nickname (NULL), created_at, last_used_at (NULL)
- **throttles** (M4): key TEXT PK (e.g. 'login:email:x@y.com'), attempts, window_started_at, locked_until (NULL). No FK.
- **audit_log** (M4): id, user_id (NULL FK, ON DELETE SET NULL), event (e.g. 'login.success'), ip, user_agent, metadata (JSON text, never secrets), created_at

Extra indexes: sessions(user_id), refresh_tokens(family_id), one_time_tokens(user_id, purpose), audit_log(user_id, created_at), oauth_accounts(user_id).

## API endpoints

JSON API under `/api/v1`, uniform errors `{error: {code, message}}`. HTML pages at root paths.

Auth (M1-M3):
- POST /api/v1/auth/register - create account (neutral response on duplicate email)
- POST /api/v1/auth/login - password login; 202 + challenge_token if TOTP enabled (M6)
- POST /api/v1/auth/logout - end current session
- POST /api/v1/auth/logout-all - end all sessions
- GET  /api/v1/auth/me - current user
- POST /api/v1/auth/verify-email/request - (re)send verification email
- POST /api/v1/auth/verify-email/confirm - consume verification token
- POST /api/v1/auth/password/forgot - always 202, no user enumeration
- POST /api/v1/auth/password/reset - consume token, set password, kill all sessions
- POST /api/v1/auth/password/change - authenticated; requires current password (sudo from M8)

Sessions (M8):
- POST /api/v1/auth/sessions/{id}/revoke - revoke one session

JWT (M5):
- POST /api/v1/auth/token - issue access (HS256, 15 min) + refresh (opaque)
- POST /api/v1/auth/token/refresh - rotate; reuse of a rotated token revokes the whole family
- POST /api/v1/auth/token/revoke

TOTP (M6):
- POST   /api/v1/auth/totp/enroll - generate secret, return otpauth URI + QR
- POST   /api/v1/auth/totp/activate - confirm with first code; returns recovery codes once
- POST   /api/v1/auth/login/2fa - consume challenge_token + code, create session
- POST   /api/v1/auth/login/2fa/recovery - login with recovery code
- POST   /api/v1/auth/recovery-codes/regenerate - sudo required
- DELETE /api/v1/auth/totp - disable 2FA, sudo required

OAuth (M7):
- GET    /login/github - redirect with state + PKCE
- GET    /login/github/callback - validate state, exchange code, link-or-create, create session
- DELETE /api/v1/auth/oauth/{provider} - unlink (forbidden if last remaining auth method)

WebAuthn (M8):
- POST /api/v1/auth/webauthn/register/options | /register/verify - sudo required
- POST /api/v1/auth/webauthn/login/options | /login/verify
- POST /api/v1/auth/sudo - elevate current session (password, TOTP code, or passkey), 10 min

HTML pages: GET/POST /signup, /login, /login/2fa, GET /verify-email, GET/POST /forgot-password, /reset-password, GET /account, GET /account/security.

## Implementation tasks

Work strictly in order. A task is done when: code + tests pass CI, mypy/ruff clean. A module is done when: its lesson doc exists in `docs/lessons/`, README updated, git tag created.

**Module 00 - Setup**
1. Init repo: uv project, pyproject with pinned deps, ruff, mypy strict, pytest, pre-commit.
   - Files: pyproject.toml, .pre-commit-config.yaml, .env.example
   - Accept: `uv sync`, `uv run ruff check .`, `uv run mypy .`, `uv run pytest` all succeed on empty skeleton.
2. Package skeleton + FastAPI app with GET /healthz; verify Swagger UI at /docs.
   - Files: authcore/, app/main.py, app/config.py, tests/
   - Accept: healthz test green; /docs renders.
3. GitHub Actions CI (lint, typecheck, tests, coverage report).
   - Files: .github/workflows/ci.yml
   - Accept: CI green on push.
4. README v1 (curriculum index, quickstart) + docs/lessons/00-project-setup.md.
   - Accept: docs exist; tag `v0.1-module-00` created after 3+4.

**Module 01 - Passwords & registration**
5. SQLAlchemy + Alembic + initial `users` migration.
   - Files: app/db.py, app/models.py, alembic/
   - Accept: `alembic upgrade head` creates users table; model test green.
6. authcore/passwords.py part 1: educational PBKDF2 (hashlib.pbkdf2_hmac, per-hash salt, self-describing storage format).
   - Accept: hash/verify round-trip tests; different salts produce different hashes; wrong password fails.
7. authcore/passwords.py part 2: Argon2id via argon2-cffi (OWASP params: m=19456 KiB, t=2, p=1), PHC prefix dispatch, needs_rehash, verify-then-rehash flow.
   - Accept: PBKDF2-stored password still verifies and is transparently rehashed to Argon2id; tests cover dispatch and rehash.
8. authcore/policy.py: min 8 / max 128 chars, no composition rules, optional common-password denylist (embedded top-1000 list).
   - Accept: policy unit tests.
9. Registration service + POST /api/v1/auth/register + /signup HTML page.
   - Files: app/services/registration.py, app/repositories/users.py, app/api/v1/auth.py, app/web/, app/templates/
   - Accept: integration test registers a user; duplicate email returns neutral response; password stored as Argon2id PHC string.
10. Lesson docs/lessons/01-passwords.md + tag `v0.2-module-01`.

**Module 02 - Sessions**
11. authcore/tokens.py: generate (secrets, >=160 bits, base32), sha256_hex helper, constant-time compare.
    - Accept: entropy/length tests; hashing deterministic.
12. `sessions` migration + repository + session service (create, validate, sliding expiry, revoke one/all).
    - Accept: expiry and sliding-window unit tests; revoked session rejected.
13. Cookie handling + get_current_user dependency (HttpOnly, Secure, SameSite=Lax, Path=/; secure flag configurable for localhost).
    - Accept: dependency returns user for valid cookie; 401 otherwise.
14. Login/logout/logout-all endpoints + /login page; new session id on every login (anti-fixation); dummy-hash verify when user not found (uniform timing); GET /api/v1/auth/me.
    - Accept: integration tests for full login/logout cycle; login response never distinguishes "no such user" from "wrong password".
15. Lesson 02-sessions.md + tag `v0.3-module-02`.

**Module 03 - Email flows**
16. docker-compose.yml with Mailpit + app/emails sender (SMTP via config) + plain-text templates.
    - Accept: test email visible in Mailpit UI; sender unit-tested with a fake SMTP transport.
17. `one_time_tokens` migration + service with atomic consume (validate + delete in one transaction).
    - Accept: token cannot be consumed twice (concurrent-safe test); expired token rejected.
18. Email verification: request/confirm endpoints + page, resend with limit.
    - Accept: full flow test sets email_verified_at.
19. Password reset: forgot/reset endpoints + pages; neutral 202 always; on reset: update hash, delete all sessions and refresh tokens, audit, notify by email.
    - Accept: flow test; sessions invalidated; response identical for existing and unknown email.
20. Authenticated password change (requires current password).
    - Accept: wrong current password is 401; other sessions invalidated.
21. Lesson 03-email-flows.md + tag `v0.4-module-03`.

**Module 04 - Hardening & PostgreSQL**
22. `throttles` migration + authcore/ratelimit.py + apply to login, forgot, verify (429 + Retry-After; progressive lockout: e.g. 5 fails -> 15 min).
    - Accept: 6th rapid login attempt gets 429; lock expires.
23. `audit_log` migration + event recording in all existing services (login.success/failed, password.reset, etc.).
    - Accept: events written; metadata never contains tokens/passwords (asserted in tests).
24. Security headers middleware + CSRF protection for HTML forms (synchronizer token bound to session).
    - Accept: form POST without CSRF token rejected; headers present on all responses.
25. PostgreSQL service in docker-compose; DATABASE_URL-driven engine; run migrations and full test suite against both SQLite and PostgreSQL (CI matrix).
    - Accept: CI green on both engines.
26. Lesson 04-hardening.md + tag `v0.5-module-04`.

**Module 05 - JWT from scratch**
27. authcore/jwt.py: base64url encode/decode, HS256 sign/verify with hmac, claims validation (exp, iat, nbf, iss, aud, leeway), reject unexpected `alg` and `none`.
    - Accept: round-trip tests; tampered header/payload/signature rejected; alg-confusion and none-attack tests; interop check against a known-good token fixture.
28. POST /api/v1/auth/token issuing 15-min access tokens.
    - Accept: token validates; expired token rejected.
29. `refresh_tokens` migration + rotation with reuse detection (reused rotated token revokes entire family, audited).
    - Accept: rotation test; reuse-detection test revokes family.
30. Bearer dependency for the API, coexisting with cookie sessions (dependency accepts either).
    - Accept: /api/v1/auth/me works with both auth methods.
31. Lesson 05-jwt.md (includes sessions-vs-JWT essay) + tag `v0.6-module-05`.

**Module 06 - TOTP from scratch**
32. authcore/totp.py: HOTP (RFC 4226) + TOTP (RFC 6238), HMAC-SHA1, 6 digits, 30 s step.
    - Accept: ALL official RFC 4226 and RFC 6238 test vectors pass.
33. Enrollment: `totp_credentials` migration, Fernet-encrypted secret (key from env), otpauth:// URI, QR via segno, activation with first valid code.
    - Accept: enroll + activate flow test; secret never returned after activation; QR endpoint returns image.
34. Two-step login: `login_challenges` migration, /login/2fa endpoint + page, window of +-1 step, last_used_step anti-replay, TOTP-specific throttling.
    - Accept: login with 2FA enabled requires second step; same code rejected twice; brute force throttled.
35. Recovery codes: migration, generate 10 hashed single-use codes, login via recovery code, regenerate (sudo from M8; until then require password re-entry).
    - Accept: recovery code works once only; regeneration invalidates old codes.
36. Lesson 06-totp.md + tag `v0.7-module-06`.

**Module 07 - OAuth 2.0 client**
37. Create GitHub OAuth App; config (GITHUB_CLIENT_ID/SECRET); setup doc.
    - Accept: .env.example updated; setup steps documented in the lesson.
38. authcore/oauth.py: authorization URL builder (state, PKCE S256), callback validation, code exchange and profile fetch via injected httpx client.
    - Accept: unit tests with mocked HTTP client; state mismatch rejected; PKCE verifier/challenge tests.
39. `oauth_accounts` migration + linking policy: existing oauth_account -> session; verified email match on both sides -> link; otherwise create new user (password_hash NULL).
    - Accept: all three linking paths covered by tests.
40. Routes /login/github + callback; link/unlink from account page; unlink forbidden if last auth method.
    - Accept: end-to-end test with mocked provider; unlink guard test.
41. Lesson 07-oauth.md + tag `v0.8-module-07`. (Optional: Google as second provider to prove the abstraction.)

**Module 08 - Passkeys & capstone**
42. py_webauthn integration: `webauthn_credentials` migration, registration ceremony (options/verify endpoints), minimal JS in app/static for navigator.credentials.
    - Accept: registration ceremony test with library-generated fixtures; credential persisted.
43. Authentication ceremony (passkey login); sign_count must increase, regression audited as possible cloning.
    - Accept: login ceremony test; decreasing sign_count flagged.
44. Sudo mode: sudo_until on session, POST /api/v1/auth/sudo (password | TOTP | passkey), enforce sudo on sensitive operations (password change, disable 2FA, delete passkey, regenerate recovery codes, unlink OAuth).
    - Accept: sensitive op without sudo returns 403 sudo_required; with sudo succeeds.
45. Capstone: /account/security page (active sessions with revoke, passkeys, 2FA status, linked accounts), docs/architecture.md, final README, coverage review (authcore >= 85%, global >= 75%).
    - Accept: page functional; coverage thresholds met in CI.
46. Lesson 08-passkeys-and-sudo.md + tag `v1.0`.

## Rules and restrictions

Security (always):
- Never store raw tokens or passwords anywhere (DB, logs, error messages, test fixtures committed with real-looking secrets). Tokens: store SHA-256 only. Passwords: Argon2id PHC only.
- All randomness via `secrets`. All secret comparisons via `hmac.compare_digest`.
- All secrets/keys via environment variables (pydantic-settings). Never commit .env.
- Auth failure messages never reveal whether an account exists (login, forgot-password, verification).
- Cookies: HttpOnly, SameSite=Lax, Secure (configurable off for localhost only), Path=/.
- One-time tokens: consume atomically (validate + delete in a single transaction).
- JWT: pin the algorithm server-side; never trust the `alg` header; reject `none`.
- Every security-relevant branch gets a test, including the attack path (tampered token, replayed code, reused refresh token, CSRF-less form post, state mismatch).

Architecture:
- `authcore` stays pure: no FastAPI, no SQLAlchemy, no network, no filesystem. HTTP clients are injected.
- Do NOT add PyJWT, python-jose, pyotp, authlib, or passlib. The hand-rolled implementations are the point of this project.
- Do not reorder or merge modules. Do not start a task whose dependencies are not done.
- New feature ideas go to the "Future work" section of the README, not into code.

Quality:
- mypy --strict and ruff must be clean before any commit. Every service function and every authcore function has tests.
- Each lesson doc follows the same structure: Concepts, Threats addressed, Design decisions, References (Copenhagen Book / OWASP / RFCs), Self-check questions.
- Everything in English.

## External services

- **GitHub OAuth App** (M7): env vars GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, OAUTH_REDIRECT_URL=http://localhost:8000/login/github/callback. No SDK; raw httpx calls to github.com/login/oauth/authorize, /access_token, api.github.com/user and /user/emails.
- **Mailpit** (M3+, docker-compose): SMTP on localhost:1025, web UI on localhost:8025. Env vars SMTP_HOST, SMTP_PORT, EMAIL_FROM.
- **PostgreSQL 16** (M4+, docker-compose): env var DATABASE_URL (defaults to SQLite file when unset).
- **Fernet key** (M6): env var TOTP_ENCRYPTION_KEY (generate with cryptography's Fernet.generate_key()).
- **WebAuthn config** (M8): RP_ID=localhost, RP_NAME=auth-anatomy, ORIGIN=http://localhost:8000 (localhost is a secure context for WebAuthn).