# How login works

This walks the password login, logout, and "log out everywhere" flows end to
end. It builds on [How a session works](sessions.md) — login is what *creates* a
session. The "why" is in the [sessions lesson](../lessons/02-sessions.md).

## The cast

| Piece | File | Role |
|---|---|---|
| Login service | [`app/services/login.py`](../../app/services/login.py) | password auth: verify, upgrade, create session |
| Endpoints | [`app/api/v1/auth.py`](../../app/api/v1/auth.py) | `POST /login`, `/logout`, `/logout-all` |
| Web page | [`app/web/login.py`](../../app/web/login.py) | `GET`/`POST /login` |
| Cookie helpers | [`app/cookies.py`](../../app/cookies.py) | set/clear the session cookie |

## The endpoint (thin by design)

`POST /api/v1/auth/login` contains no business logic — it delegates to the login
service and only translates the result into HTTP:

```python
@router.post("/login")
def post_login(payload, request, response, db) -> StatusResponse:
    raw_token = login(db, email=payload.email, password=payload.password,
                      ip=_client_ip(request), user_agent=request.headers.get("user-agent"))
    if raw_token is None:
        raise ApiError(401, "invalid_credentials", "Invalid email or password.")
    set_session_cookie(response, raw_token)
    return StatusResponse(status="ok")
```

Two things to notice:

- **One generic failure.** Any failure — unknown email, wrong password,
  OAuth-only account — becomes the *same* `401 invalid_credentials`. The endpoint
  never distinguishes them, so it cannot be used to probe which emails exist.
- **The cookie is the only thing sent back.** On success the raw token goes into
  the `session` cookie via `set_session_cookie` (HttpOnly, Secure, SameSite=Lax);
  the body is just `{"status": "ok"}`.

## The service (where the security lives)

`login` ([`app/services/login.py`](../../app/services/login.py)) returns a new
session's raw token, or `None`:

```python
user = UsersRepository(db).get_by_email(email.strip().lower())

if user is None or user.password_hash is None:
    passwords.verify_password(password, _DUMMY_HASH)   # timing equalizer
    return None

stored_hash = user.password_hash
if not passwords.verify_password(password, stored_hash):
    return None

if passwords.needs_rehash(stored_hash):                # verify-then-rehash
    user.password_hash = passwords.hash_password(password)

return create_session(db, user_id=user.id, ip=ip, user_agent=user_agent)
```

Three security properties are built into these lines:

### 1. Uniform timing / no user enumeration

If there is no user, or the user is OAuth-only (`password_hash is None`), there is
nothing real to check — but returning immediately would make the "no such account"
case *faster* than a real password check, and an attacker timing the responses
could harvest which emails exist. So the service verifies the submitted password
against a module-level **dummy Argon2id hash** (`_DUMMY_HASH`), spending the same
work, and only then returns `None`. Combined with the endpoint's single generic
error, the existence of an account leaks through neither the body nor the timing.

### 2. Verify-then-rehash

Once the password is confirmed, `needs_rehash` asks whether the stored hash is
below the current standard (a legacy PBKDF2 hash, or Argon2id with outdated
parameters — see [How a session works](sessions.md) and the module 01 lesson). If
so, the plaintext — available for this one instant — is re-hashed with today's
Argon2id and written back. The user is silently upgraded on login. This is the
first place the module 01 machinery is actually exercised.

### 3. Anti session-fixation

The service always calls `create_session`, which mints a **fresh** token. It
never reads or reuses an incoming cookie. In a session-fixation attack, the
attacker plants a known session id in the victim's browser and hopes it becomes
authenticated on login; issuing a brand-new id on every login defeats it. The
test `test_login_issues_a_new_session_each_time` plants a cookie and asserts the
post-login token differs from it.

A subtle detail: the `needs_rehash` write and the new session row are both
persisted by the single `db.commit()` inside `create_session` — one transaction.

## Logout and logout-all

Both are thin endpoints over the session service's revocation (see
[How a session works](sessions.md#4-revocation)):

- `POST /logout` reads the cookie, calls `revoke_session` (delete this row), and
  clears the cookie. It does not require a valid session — logging out is always
  safe.
- `POST /logout-all` depends on `get_current_user`, then calls
  `revoke_all_sessions(user.id)` (delete every row for the user) and clears the
  cookie. This is what password reset and similar events reuse to sign a user out
  of every device.

After either, the deleted session(s) fail the next `validate_session` lookup, and
the client's now-useless cookie is gone.
