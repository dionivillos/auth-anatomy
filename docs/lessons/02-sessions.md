# 02 — Sessions from scratch

How this system authenticates a user across requests with server-side sessions:
a high-entropy token stored only as its hash, carried in a hardened cookie,
expiring on two independent clocks, and issued by a login flow that resists
enumeration and fixation. The "how it works" companion lives in the reference
docs ([sessions](../reference/sessions.md), [login](../reference/login.md)).

## Concepts

### What a server-side session is

After a user proves who they are (password today, more factors later), the server
needs to remember them across requests without asking for the password every
time. A **server-side session** does this by storing the session state in the
database and handing the client only an opaque **session token** — a long random
string with no meaning of its own. On each request the client sends the token
back (in a cookie, task 13) and the server looks up the matching session.

This is the opposite of a stateless token like a JWT (module 5), which carries
its own claims and is verified by signature without a database lookup. The
trade-off in one line: server-side sessions are trivially **revocable** (delete
the row) but require a lookup per request; JWTs need no lookup but are hard to
revoke before they expire.

### The token, and why only its hash is stored

The session token must be **unguessable** and it must **not be recoverable from a
database leak**:

- **Unguessable** ⇒ high entropy from a CSPRNG. We use 160 bits from `secrets`,
  base32-encoded to a 32-character, cookie-safe string. (See the box below for
  why 160 bits and why base32.)
- **Not recoverable from a leak** ⇒ the database stores only `sha256(token)`, the
  same idea as password hashing. A stolen sessions table therefore contains no
  usable tokens; an attacker would have to invert SHA-256. When a token arrives,
  the server hashes it and looks that hash up.

Comparisons of secret-derived values use `hmac.compare_digest` (constant time),
never `==`, so response timing cannot reveal how many leading characters matched.

#### Entropy and base32, concretely

- **Entropy** is the size of the space a value is drawn from. 160 bits ⇒ 2^160
  (~1.46 × 10^48) equally likely tokens — brute-forcing one is infeasible even at
  billions of guesses per second. OWASP recommends at least 128 bits for a
  session id; 160 is a comfortable margin (and 20 bytes lands on a clean base32
  boundary).
- **base32** uses a 32-symbol alphabet (A–Z, 2–7), so each character encodes
  log2(32) = **5 bits**. 160 bits ÷ 5 = 32 characters, with no `=` padding
  because 20 bytes is a multiple of 5. It stays case-insensitive and free of
  cookie/URL-hostile characters (`+`, `/`, `=`), unlike base64.

### Session lifetime: two independent deadlines

A session carries two clocks, and it dies when **either** runs out:

- **Absolute lifetime** — a fixed cap from creation (`expires_at = created_at +
  ABSOLUTE_LIFETIME`). However actively the session is used, it eventually forces
  a fresh login. This bounds the useful life of a token that was silently stolen.
- **Idle timeout (sliding)** — the session dies if unused for `IDLE_TIMEOUT`.
  Every successful use slides the window forward by setting `last_used_at = now`.
  This logs out abandoned sessions without punishing active users.

Keeping both is deliberate: the sliding window is convenient but, alone, would let
a stolen-but-kept-warm token live forever; the absolute cap closes that.

### Revocation

Because the state lives server-side, revoking a session is just deleting its row:
logout deletes the current session, "log out everywhere" deletes all rows for the
user, and a missing row simply fails the lookup on the next request. Password
reset and similar events (later modules) use "delete all sessions" to kick every
device out.

### Carrying the token: the cookie flags

The token travels in a cookie, and each flag closes a specific attack:

- **`HttpOnly`** — JavaScript cannot read the cookie, so a cross-site scripting
  (XSS) bug on the page cannot exfiltrate the session token.
- **`Secure`** — the cookie is sent only over HTTPS, so it cannot be captured from
  plaintext traffic. It is configurable off for `localhost` only, where there is
  no TLS in development.
- **`SameSite=Lax`** — the browser does not attach the cookie to cross-site
  subrequests (a form auto-submitted from `evil.com`), which blocks the classic
  cross-site request forgery (CSRF) vector, while still sending it on top-level
  navigations to the site so normal links keep working.
- **`Path=/`** — the cookie is valid for the whole application.

The server reads the cookie through one dependency, `get_current_user`, which
looks the session up and either yields the `User` or returns `401`. That 401 is
identical whether the cookie is absent or invalid — it never reveals which.

### Login: fixation and timing

Creating a session at login has two non-obvious security requirements:

- **Anti session-fixation.** In a fixation attack the attacker plants a known
  session id in the victim's browser *before* they log in, hoping the server will
  simply mark that id as authenticated. The defence is to always mint a **new**
  session id on login and never adopt an incoming one. Our login always calls
  `create_session` (a fresh token) and ignores any existing cookie.
- **Uniform timing / no enumeration.** Login must not reveal whether an email has
  an account — not through the response, and not through *how long it takes*. A
  correct password check runs an expensive Argon2 verification; if the "no such
  user" path returned immediately, it would be measurably faster, letting an
  attacker harvest valid emails by timing. So when there is no user (or the
  account has no password), login still verifies the submitted password against a
  fixed **dummy hash**, spending the same time, and returns the same generic
  error as a wrong password.

Login is also where the module 01 **verify-then-rehash** upgrade finally runs: on
a successful check, if the stored hash is outdated it is transparently re-hashed
to current Argon2id.

## Threats addressed

- **Session token guessing / brute force.** 160 bits of CSPRNG entropy make a
  valid token computationally impossible to guess.
- **Token theft via a database leak.** Only `sha256(token)` is stored, so a
  leaked sessions table yields no usable tokens.
- **Timing side channels on token comparison.** Constant-time comparison avoids
  leaking match progress.
- **Indefinitely long-lived / stolen sessions.** The absolute lifetime caps how
  long any session (including a silently stolen one) can live; the idle timeout
  retires abandoned sessions.
- **Inability to log out.** Server-side state makes revocation immediate and
  complete (single session or all sessions).
- **Token theft via XSS.** `HttpOnly` keeps the token out of reach of JavaScript.
- **Token capture in transit.** `Secure` restricts the cookie to HTTPS.
- **Cross-site request forgery (CSRF).** `SameSite=Lax` withholds the cookie from
  cross-site subrequests.
- **Session fixation.** A brand-new session id on every login means a pre-planted
  id is never honoured.
- **Account enumeration via login.** A single generic error plus equalized timing
  (dummy-hash verification) mean login does not reveal which emails exist.

## Design decisions

- **Opaque token + server-side state, not a self-describing token.** Chosen for
  immediate revocability; the sessions-vs-JWT trade-off is revisited in module 5.
- **160-bit base32 token; store only the SHA-256.** Entropy margin, cookie-safe
  encoding, and no usable secret at rest — see Concepts.
- **Two deadlines (absolute + sliding idle), combined with OR.** `is_expired`
  trips when either deadline passes; the two guard different failure modes.
- **Expiry rules live in pure `authcore`, persistence in the app layer.**
  `authcore/sessions.py` decides deadlines and validity from plain datetimes and
  has no database or framework imports, so the rules are unit-tested in isolation.
- **Revoke by deleting the row.** No `revoked_at` column; absence is the signal.
- **Model named `UserSession`.** The table is `sessions`, but the class avoids a
  name clash with SQLAlchemy's own `Session`.
- **Datetimes normalized to UTC-aware in the service.** SQLite returns naive
  datetimes; the service attaches UTC before handing them to the pure rules, which
  require timezone-aware values. On PostgreSQL this is a no-op.
- **The cookie carries the token; every flag is deliberate.** HttpOnly, Secure
  (off only for localhost), SameSite=Lax, Path=/ — each maps to a specific threat.
- **One `get_current_user` dependency, one uniform 401.** A single place reads the
  cookie and resolves the user; the 401 is identical for an absent or invalid
  session so it never leaks session state.
- **Login always mints a new session and equalizes timing.** Anti-fixation and
  anti-enumeration are properties of the login service, not the endpoint, which
  stays thin and returns a single generic error.

## References

- [OWASP — Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [The Copenhagen Book — Sessions](https://thecopenhagenbook.com/sessions)
- [OWASP — Session ID entropy and length](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#session-id-entropy)
- [OWASP — Session fixation](https://owasp.org/www-community/attacks/Session_fixation)
- [MDN — Set-Cookie: HttpOnly, Secure, SameSite](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie)
- [OWASP — Cross-Site Request Forgery (CSRF)](https://owasp.org/www-community/attacks/csrf)

## Self-check questions

1. Why is only `sha256(token)` stored in the database rather than the token
   itself, and what does that protect against?
2. What is the difference between the absolute lifetime and the idle timeout, and
   why keep both instead of just the sliding one?
3. Why does `is_expired` combine the two deadlines with OR rather than AND?
4. Why base32 for the token instead of hex or base64, and why exactly 32
   characters for 160 bits?
5. How is a session revoked in this design, and why does "log out everywhere"
   need nothing more than that mechanism?
6. Why do the expiry rules live in pure `authcore` while the sliding update and
   deletion of expired sessions live in the app service?
7. What specific attack does each cookie flag address: `HttpOnly`, `Secure`,
   `SameSite=Lax`?
8. What is a session fixation attack, and what single measure in the login flow
   defeats it?
9. Why does login verify the password against a dummy hash when the email does
   not exist, instead of returning immediately?
10. Why is the `401` from `get_current_user` identical whether the session cookie
    is absent or merely invalid?

## Exercises

Hands-on coding exercises that extend this module live in
[`../../exercises/02-sessions/`](../../exercises/02-sessions/): editable `.py`
files with their own tests and reference solutions. Run them with
`uv run pytest exercises/02-sessions`.
