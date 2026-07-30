# Answers — 01 Passwords & registration

Answers to the self-check questions in [`../01-passwords.md`](../01-passwords.md). Try to answer
from memory first; use this only to check yourself afterward.

**1. Why does a per-hash salt make two identical passwords produce different stored strings, and
why does that matter beyond rainbow-table defense?**

The salt is mixed into the derivation, so `derive("hunter2", saltA)` and `derive("hunter2", saltB)`
produce different outputs even though the password is the same. Because each hash draws a fresh
random salt, two users who both chose "hunter2" end up with completely different stored strings.
Beyond defeating precomputed (rainbow) tables, this breaks **correlation**: an attacker who steals
the database cannot tell which accounts share a password, cannot prioritize cracking the most
common one and reusing the result, and cannot confirm that a password they cracked for user A also
belongs to user B just by comparing hashes.

**2. When verifying a password, why must the iteration count and salt be read from the stored string
rather than from the current module constants?**

Because the stored hash was created with whatever parameters were current *at the time it was
made*, and those may no longer match the module constants. If you raised the iteration count from
600,000 to 800,000 last month, every hash created before then still holds `600000`. To recompute
the same derived key you must use the *same* salt and the *same* iteration count that produced it —
which only exist inside the stored string. Reading from the module constants would recompute a
different key and reject a correct password. The module constants describe how to build a *new*
hash; the stored string describes how to verify an *existing* one.

**3. Why is `hmac.compare_digest` used instead of `==` when comparing the derived key against the
stored one?**

`==` on bytes short-circuits: it returns `False` at the first differing byte. The time it takes
therefore depends on how many leading bytes matched, and an attacker who can measure that timing
can recover the correct value byte by byte (a timing side-channel attack). `hmac.compare_digest`
compares in constant time — its duration does not depend on where or whether the values first
differ — so no information leaks through timing. Any comparison of secret-derived values must use
it.

**4. A freshly created Argon2id hash returns `needs_rehash() == False`, but one created with weaker
parameters returns `True`. What exactly is being compared, and where do the "weaker parameters"
come from?**

An Argon2id hash string embeds the parameters it was made with (`m=…,t=…,p=…`). `check_needs_rehash`
compares *those embedded parameters* against the parameters of the configured `_argon2_hasher`
(the current standard). A fresh hash was just produced by that same hasher, so its embedded
parameters equal the current ones → no rehash needed → `False`. A hash made by a different, weaker
hasher (for example `m=8, t=1`) embeds smaller numbers that differ from the current configuration
→ it is below standard → `True`. The "weaker parameters" come from the hash having been created
earlier, when the system's configured cost was lower (simulated in the tests with a deliberately
weak hasher). The same function also flags every legacy PBKDF2 hash, since any PBKDF2 hash is by
definition below the current Argon2id standard.

**5. Why is PBKDF2 hand-rolled in this project while Argon2id is delegated to a library — and where
is the line between "the primitive" and "the design"?**

PBKDF2 is hand-rolled purely for teaching: it makes the moving parts visible (generate a salt,
iterate a KDF, encode a self-describing string, compare in constant time). Argon2id is delegated to
`argon2-cffi` because implementing a memory-hard primitive correctly and safely is genuinely hard
and error-prone — rolling your own crypto primitive is a classic footgun. The **primitive** is the
raw derivation function (PBKDF2's HMAC loop, Argon2's memory-hard core); you should reach for a
vetted implementation of that. The **design** is everything around it: the storage format, prefix
dispatch, `needs_rehash`, the verify-then-rehash upgrade path, parameter choices, constant-time
comparison. That design is what this project owns and what actually determines whether the system
is secure and maintainable.

**6. Why must the verify-then-rehash upgrade happen during login rather than in a background job
that walks the users table?**

Because rehashing requires the **plaintext password**, and the only moment the server ever holds it
is during a successful login, when the user has just submitted it. The stored value is a one-way
hash by design — a background job walking the users table has no way to recover anyone's password
and therefore nothing to rehash. So the upgrade is inherently opportunistic: it can only happen for
a given user the next time that user logs in successfully.

**7. Why does NIST 800-63B recommend against composition rules ("one uppercase, one digit, one
symbol"), and what is recommended instead?**

Composition rules add very little real entropy while actively harming usability and, paradoxically,
security. Faced with "must contain an uppercase letter, a digit, and a symbol," people converge on a
small set of predictable transformations (`password` → `Password1!`), and attackers' cracking tools
encode exactly those rules, so the "complex" passwords fall quickly. The rules also frustrate users
into reuse and note-keeping. NIST instead recommends allowing long passphrases, screening candidates
against lists of common and previously-breached passwords, and not forcing periodic rotation. In
short: measure length and check a denylist; do not dictate character shape.

**8. The maximum password length is 128. Give the real reason for an upper bound — it is not "longer
passwords are weaker."**

The cap protects the server, not the password. Password hashing is intentionally expensive, so if
you accept arbitrarily long input, an attacker can submit a multi-megabyte "password" and force you
to hash it, burning CPU/memory on every attempt — a denial-of-service vector. A generous but finite
bound (128 characters) also keeps input within the hashing algorithm's limits. The right behaviour is
to reject over-length input, never to silently truncate it (truncation would quietly discard entropy
the user believed they had).

**9. Why is the common-password denylist embedded as a Python `frozenset` and passed as a parameter,
rather than read from a file inside `check_password`?**

Two reasons. First, `authcore` is pure by contract — no filesystem, no I/O — so reading a file at
runtime would violate the boundary that keeps the domain logic fast and trivially testable; embedding
the list as a casefolded `frozenset` literal keeps membership tests O(1) and dependency-free. Second,
injecting the denylist as a parameter (defaulting to the embedded one) makes the policy configurable
and testable: a test can pass a tiny custom set to prove both that an injected word is rejected and
that the default was *replaced* rather than merged, and a real deployment could swap in the full
top-1000 (or a live breached-password feed) without changing `check_password` at all.

**10. Why does registration return an identical response for a new email and an already-registered
one, and what would leak if it did not?**

If the two responses differed — a different status code, message, or even a noticeably different
response time — an attacker could submit a list of email addresses and read off which ones already
have accounts. That is **account enumeration**, and the harvested list feeds phishing, credential
stuffing, and targeted attacks. Returning the same response in both cases (and doing the same
expensive work on both paths, so timing does not betray the answer) keeps the existence of an account
private. This is the same anti-enumeration principle applied later to login and password-reset flows.

**11. Why is a duplicate email handled by catching the database's `IntegrityError` rather than by
first checking whether the email exists? Name the race this avoids.**

A "check then insert" has a **TOCTOU (time-of-check to time-of-use)** race: between the moment you
check "does this email exist?" and the moment you insert, another concurrent request can insert the
same email. Both requests see "free," both try to insert, and you get either a crash or a duplicate,
depending on constraints. The database's UNIQUE constraint is the only thing that can serialise the
two safely: you attempt the insert, and exactly one wins while the other receives an `IntegrityError`,
which the service treats as a neutral success. This is both race-free and non-enumerating.

**12. In the registration flow, why must the repository not call `commit()` and the service must?**

Because a single use case often spans several repository operations that must succeed or fail as a
unit, and only the layer that understands the *use case* — the service — knows where that unit begins
and ends. If repositories committed on their own, the service could not compose them atomically or
roll back cleanly when, say, the insert hits a duplicate. Keeping `commit`/`rollback` in the service
puts the transaction boundary in exactly one place, so the whole registration either lands atomically
or leaves no trace.
