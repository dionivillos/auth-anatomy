# Answers — 02 Sessions from scratch

Answers to the self-check questions in [`../02-sessions.md`](../02-sessions.md). Try to answer from
memory first; use this only to check yourself afterward.

**1. Why is only `sha256(token)` stored in the database rather than the token itself, and what does
that protect against?**

So that a database leak yields no usable session tokens. The token is a bearer credential: anyone
who has it is treated as the logged-in user. If the raw tokens were stored, an attacker who read the
sessions table could immediately impersonate every active user. Storing only the SHA-256 means the
table contains one-way hashes; to use them an attacker would have to invert SHA-256, which is
infeasible. It is the same reasoning as password hashing, applied to session tokens. Verification
still works because hashing is deterministic: hash the presented token and look that hash up.

**2. What is the difference between the absolute lifetime and the idle timeout, and why keep both
instead of just the sliding one?**

The **absolute lifetime** is a fixed cap measured from creation (`expires_at = created_at +
ABSOLUTE_LIFETIME`); the session expires then no matter how much it is used. The **idle timeout** is
a sliding window measured from the last use (`last_used_at + IDLE_TIMEOUT`); every use pushes it
forward. The idle timeout alone is convenient but dangerous: a token that was stolen and kept
"warm" by periodic use would never expire. The absolute cap closes that hole by guaranteeing every
session eventually forces a fresh authentication, bounding the damage of a silent theft.

**3. Why does `is_expired` combine the two deadlines with OR rather than AND?**

Because the session must be invalid as soon as *either* deadline passes. With OR, reaching the
absolute deadline OR the idle deadline expires the session — which is what "two independent limits"
means. With AND it would only expire once *both* had passed, so a long-idle session would still be
accepted as long as the absolute cap had not been hit (and vice versa), defeating the point of
having two limits.

**4. Why base32 for the token instead of hex or base64, and why exactly 32 characters for 160
bits?**

base32 uses a 32-symbol alphabet (A–Z, 2–7), so each character carries log2(32) = 5 bits, and it
avoids characters that are awkward in cookies/URLs (`+`, `/`, `=`) while staying case-insensitive.
hex would carry only 4 bits per character (40 characters for 160 bits — longer), and base64 packs 6
bits per character but reintroduces URL-hostile symbols. 160 bits ÷ 5 bits per character = 32
characters, and because 20 bytes is a multiple of 5, base32 needs no `=` padding — a clean 32-char
token.

**5. How is a session revoked in this design, and why does "log out everywhere" need nothing more
than that mechanism?**

A session is revoked by deleting its row; there is no `revoked_at` flag, and the next lookup simply
fails to find it. Because the session state lives entirely server-side, "log out everywhere" is just
"delete all rows for this user" — the same delete operation applied to the whole set. Nothing on the
client needs to be trusted or contacted; removing the server-side state is sufficient and immediate,
which is exactly what stateless tokens (JWTs) cannot do cheaply.

**6. Why do the expiry rules live in pure `authcore` while the sliding update and deletion of expired
sessions live in the app service?**

`authcore` is pure domain logic: given plain datetimes it decides deadlines and whether a session is
expired, with no database, framework, or clock side effects — which makes those rules fast and
trivial to unit-test, including boundary cases. Actually *doing* something about the result (writing
`last_used_at` back, deleting an expired row, committing) is I/O and belongs to the app service,
which owns the transaction. This keeps the security-critical decision logic isolated and testable
and keeps side effects at the edges.

**7. What specific attack does each cookie flag address: `HttpOnly`, `Secure`, `SameSite=Lax`?**

- **`HttpOnly`** addresses **token theft via XSS**: JavaScript running on the page (injected through a
  cross-site scripting bug) cannot read an HttpOnly cookie, so it cannot exfiltrate the session token.
- **`Secure`** addresses **capture in transit**: the cookie is only ever sent over HTTPS, so it cannot
  be sniffed from plaintext HTTP. (It is disabled for localhost only, where dev has no TLS.)
- **`SameSite=Lax`** addresses **CSRF**: the browser will not attach the cookie to cross-site
  subrequests (e.g. a form on `evil.com` auto-posting to your API), so an attacker cannot ride a
  logged-in user's session, while top-level navigations to your site still send it.

**8. What is a session fixation attack, and what single measure in the login flow defeats it?**

In a session fixation attack the attacker first obtains or chooses a session id, plants it in the
victim's browser (e.g. via a crafted link or a set-cookie they control), and waits for the victim to
log in. If the server were to authenticate *that same* id, the attacker — who already knows it — would
now hold a valid logged-in session. The single defeating measure is to **issue a brand-new session id
on every successful login** and never adopt an incoming one, which our login does by always calling
`create_session`. The planted id is never associated with the authenticated user.

**9. Why does login verify the password against a dummy hash when the email does not exist, instead
of returning immediately?**

To keep the response *time* independent of whether the account exists. Verifying a real password runs
an expensive Argon2 computation; if the "no such user" branch returned immediately it would be
noticeably faster, and an attacker measuring response times could tell which emails are registered — a
timing side channel that enables enumeration. Verifying the submitted password against a fixed dummy
Argon2 hash spends the same work on the non-existent-user path, so both paths take about the same time
and return the same generic error. (It is the login-time counterpart of the dummy-hash idea; the
registration flow protects enumeration with a neutral duplicate response instead.)

**10. Why is the `401` from `get_current_user` identical whether the session cookie is absent or
merely invalid?**

Because distinguishing them would leak information without any benefit. A different response for
"no cookie" versus "cookie present but not a valid session" would tell an attacker probing with guessed
tokens that they had at least hit the right *shape* or a once-valid id, and it complicates client
handling for no reason. Both cases mean the same thing operationally — "you are not authenticated" — so
both return the same `401 not_authenticated`.
