# How a session works

This walks a session through its whole life — creation, storage, validation on
each request, sliding expiry, and revocation — naming the exact code at each
step. It is the "how" companion to the [sessions lesson](../lessons/02-sessions.md),
which covers the "why".

## The cast

| Piece | File | Role |
|---|---|---|
| Token primitives | [`authcore/tokens.py`](../../authcore/tokens.py) | generate, hash, constant-time compare |
| Expiry rules | [`authcore/sessions.py`](../../authcore/sessions.py) | pure deadline logic (no I/O) |
| Model | [`app/models.py`](../../app/models.py) (`UserSession`) | the `sessions` table |
| Repository | [`app/repositories/sessions.py`](../../app/repositories/sessions.py) | data access, never commits |
| Service | [`app/services/sessions.py`](../../app/services/sessions.py) | orchestration, owns the transaction |
| Cookie helpers | [`app/cookies.py`](../../app/cookies.py) | set/clear the cookie with security flags |
| Dependency | [`app/dependencies.py`](../../app/dependencies.py) | `get_current_user` |

The golden rule throughout: **the raw token exists only in the client's cookie;
the database stores only its SHA-256 hash.**

## 1. Creating a session

`create_session` runs after a successful login (module 14 wires the login
endpoint to it). Reading it top to bottom:

```python
def create_session(db, *, user_id, ip=None, user_agent=None, now=None) -> str:
    now = now or _now()
    raw_token = tokens.generate()                     # 160-bit base32 string
    SessionsRepository(db).create(
        token_hash=tokens.sha256_hex(raw_token),      # only the hash is stored
        user_id=user_id,
        created_at=now,
        expires_at=session_rules.absolute_expiry(now),# created_at + ABSOLUTE_LIFETIME
        last_used_at=now,
        ip=ip,
        user_agent=user_agent,
    )
    db.commit()
    return raw_token                                  # returned to set in the cookie
```

Step by step:

- `now = now or _now()` — the current time is a parameter with a default. Injecting
  it is what lets the tests fast-forward the clock to check expiry without waiting.
- `tokens.generate()` — a fresh 160-bit random token (see
  [tokens](../../authcore/tokens.py)). This is the only place the raw value is
  produced.
- `tokens.sha256_hex(raw_token)` — the value actually written to the row. If the
  database leaks, these hashes are useless to an attacker.
- `session_rules.absolute_expiry(now)` — delegates the *policy* (how long a
  session may live) to the pure rules in `authcore`. The service does not hard-code
  `+ 30 days`; it asks the rules.
- `db.commit()` — the **service** commits. The repository only added and flushed.
- `return raw_token` — the caller (the login endpoint) passes this to
  `set_session_cookie`, which is the only time the raw token leaves the server.

The repository's `create` is deliberately dumb — build the row, `add`, `flush`,
return it. `flush` sends the INSERT so a duplicate `token_hash` would raise here,
but it does not end the transaction; the service still owns `commit`/`rollback`.

## 2. Sending it to the client

The login endpoint calls `set_session_cookie(response, raw_token)`
([`app/cookies.py`](../../app/cookies.py)), which sets the `session` cookie with:

- `HttpOnly` — JavaScript cannot read it (an XSS bug cannot steal the token).
- `Secure` — HTTPS only (configurable off for localhost via `secure_cookies`).
- `SameSite=Lax` — not sent on cross-site subrequests, mitigating CSRF.
- `Path=/` and a `Max-Age` matching the absolute lifetime.

From here the browser sends the cookie back on every request to the site.

## 3. Validating on each request

Any protected route depends on `get_current_user`
([`app/dependencies.py`](../../app/dependencies.py)), which reads the cookie and
calls `validate_session`. The service is where the interesting logic lives:

```python
def validate_session(db, raw_token, *, now=None) -> User | None:
    now = now or _now()
    repo = SessionsRepository(db)
    row = repo.get_by_token_hash(tokens.sha256_hex(raw_token))   # look up by hash
    if row is None:
        return None                                             # unknown token

    if session_rules.is_expired(
        now,
        expires_at=_as_utc(row.expires_at),
        last_used_at=_as_utc(row.last_used_at),
    ):
        repo.delete(row)                                        # clean up expired
        db.commit()
        return None

    row.last_used_at = now                                      # slide idle window
    db.commit()
    return db.get(User, row.user_id)
```

The reasoning behind each line:

- **Look up by hash, not by raw token.** The presented token is hashed and the
  row is found by `token_hash`. There is no reversible lookup of the raw value
  anywhere.
- **Unknown → `None`.** A token that hashes to no row (fake, or already revoked
  and deleted) is simply not a session.
- **Expiry is decided by pure rules.** `session_rules.is_expired` gets plain
  datetimes and returns a bool; it knows nothing about the database. It trips when
  *either* deadline has passed — the absolute `expires_at`, or the idle deadline
  `last_used_at + IDLE_TIMEOUT` (see [expiry rules](../../authcore/sessions.py)).
- **Expired sessions are deleted, then rejected.** Rather than leave dead rows
  around, validation removes an expired session as it rejects it.
- **`_as_utc(...)` — the SQLite timezone detail.** SQLite returns naive datetimes
  (it does not persist the timezone). The pure rules require timezone-aware UTC, so
  the service attaches UTC to a naive value before calling them. On PostgreSQL
  (module 04+) the values already carry UTC and this is a no-op.
- **Sliding the window.** On a valid session, `last_used_at = now` pushes the idle
  deadline forward, then `commit()` persists it. An actively used session therefore
  never hits the idle timeout; only the absolute deadline can end it.
- **Return the user.** `db.get(User, row.user_id)` loads the owner, which
  `get_current_user` hands to the route.

## 4. Revocation

Because the state is server-side, revoking is just deleting rows:

```python
def revoke_session(db, raw_token) -> None:        # logout: this session
    row = SessionsRepository(db).get_by_token_hash(tokens.sha256_hex(raw_token))
    if row is not None:
        SessionsRepository(db).delete(row)
        db.commit()

def revoke_all_sessions(db, user_id) -> None:     # logout everywhere
    SessionsRepository(db).delete_all_for_user(user_id)
    db.commit()
```

After deletion, the next `validate_session` finds no row and returns `None`. On
logout the endpoint also calls `clear_session_cookie` so the client discards its
now-useless token. `revoke_all_sessions` is what password reset and similar events
use to kick every device out at once.

## Why the split (service vs authcore)

Notice the division of labour:

- **`authcore/sessions.py`** answers pure questions: *what is the absolute
  deadline?* *is this expired at time `now`?* No database, no clock, no framework —
  so it is unit-tested exhaustively, boundaries included, in microseconds.
- **`app/services/sessions.py`** does the I/O around those answers: generate,
  hash, read/write rows, commit, normalize SQLite datetimes, load the user.

That is the dependency rule from the [architecture](architecture.md) in miniature:
the security-critical decision is pure and isolated; the side effects live at the
edge.
