# 01 — Passwords & registration

How this system stores passwords and registers accounts: an educational PBKDF2
implementation, production Argon2id with a transparent upgrade path, a
NIST-aligned password policy, and a registration flow that does not leak which
accounts exist. Covers the `authcore.passwords`, `authcore.policy`, and
registration-service code built in this module.

## Concepts

### What "storing a password" actually means

You never store the password. You store a one-way function of it: a value from
which the password cannot practically be recovered, but which you can recompute
from a login attempt to check whether it matches. The whole subject is about
choosing a function that is *cheap for you to compute once per login* but
*ruinously expensive for an attacker to invert billions of times* after they
steal your database.

### Salt

A **salt** is a random value generated fresh for every password and stored
alongside the hash. It is not secret. It does two things:

- **Defeats precomputation.** Without a salt, an attacker precomputes a table of
  `hash(common_password)` once (a "rainbow table") and looks up every stolen
  hash instantly. A unique salt per password means their precomputation is
  worthless — they would need a separate table per salt.
- **Breaks cross-account correlation.** With a per-hash salt, two users with the
  same password get *different* stored strings, so a breach never reveals which
  accounts share a password.

All salts come from `secrets` (a CSPRNG), never `random`.

### Fast hash vs password hash (KDF)

`SHA-256` is a *fast* hash — that is exactly what you do **not** want here. A GPU
computes billions of SHA-256 per second, so a fast hash barely slows an attacker
down. A **password hashing function** (a key derivation function, KDF) is
*deliberately* slow and/or memory-hungry:

- **PBKDF2** (task 6, educational) iterates HMAC-SHA256 many times. Its only cost
  knob is the **iteration count** (CPU work). We use OWASP's recommendation of
  600,000 iterations. PBKDF2 is CPU-bound, which makes it comparatively cheap to
  accelerate on GPUs/ASICs — that is its weakness.
- **Argon2id** (task 7, production) is **memory-hard**: it forces the attacker to
  use a large amount of RAM per guess, which is what neutralizes cheap massively
  parallel hardware. Its cost is three numbers: memory, time (iterations), and
  parallelism. We use OWASP's parameters `m=19456 KiB, t=2, p=1`.

### Self-describing storage format (PHC-style)

Both algorithms store everything needed to verify in a single string:

```
pbkdf2_sha256$600000$<salt_b64>$<hash_b64>
$argon2id$v=19$m=19456,t=2,p=1$<salt_b64>$<hash_b64>
```

Algorithm, parameters, salt, and the derived hash all travel together. Two
consequences follow directly from this:

- **Verification needs no external configuration.** You read the salt and the
  cost parameters *out of the stored string* and recompute with exactly those.
- **Old hashes keep working when you raise the cost.** Because each hash records
  the parameters it was made with, bumping the global cost later does not
  invalidate a single existing hash — each is checked against its own numbers.

### Algorithm agility

Real systems must move to stronger algorithms without asking users to reset
their passwords. Three pieces make that possible:

- **Dispatch by prefix.** `verify_password` looks at the leading tag
  (`$argon2…` vs `pbkdf2_sha256$…`) and routes to the right verifier. This is
  why the storage format leads with an algorithm tag.
- **`needs_rehash`.** Given a stored hash, decide whether it is below today's
  standard: a legacy PBKDF2 hash always is; an Argon2id hash is only if its
  embedded parameters differ from the ones configured now.
- **Verify-then-rehash.** On a *successful* login you hold the plaintext for one
  instant. If `needs_rehash` is true, you rehash that plaintext with the current
  algorithm/parameters and overwrite the stored value. The user notices nothing.

### Password policy (NIST SP 800-63B)

Modern guidance inverts the old "complexity" advice:

- **Length over composition.** A length floor (here, 8 characters) matters; rules
  like "must contain an uppercase letter, a digit, and a symbol" do not. They add
  almost no real entropy and push users toward predictable shapes (`Password1!`,
  `Summer2024!`) that rule-based crackers exploit directly. This project imposes
  **no composition rules** by design.
- **Block common passwords.** The single most effective policy is rejecting
  known-common and previously-breached passwords, because that is exactly what
  credential-stuffing and dictionary attacks try first. A denylist targets the
  real threat that composition rules only pretend to.
- **Cap the maximum length, but not for strength.** An upper bound (128) bounds
  the cost of hashing an attacker-supplied input (a DoS vector) and stays within
  the hashing algorithm's limits — not because longer passwords are weaker. Never
  truncate silently; reject instead.

### Registration without account enumeration

Registration is the first place an attacker probes to learn *which email
addresses have accounts* — information useful for phishing, credential stuffing,
and targeted attacks. The defence is a **neutral response**: the endpoint returns
exactly the same thing whether the email was newly registered or already existed.

Two implementation details make that neutrality real:

- **Attempt-and-catch, not check-then-insert.** You do *not* query "does this
  email exist?" and branch on the answer. You attempt the insert and catch the
  database's UNIQUE-constraint violation. Besides being neutral, this closes a
  **TOCTOU (time-of-check to time-of-use) race**: two concurrent signups for the
  same email could both pass a prior existence check and then both try to insert.
  Only the database constraint can serialise them — one commits, the other gets
  an `IntegrityError` and is treated as a (neutral) success.
- **Constant-ish work on both paths.** The policy check and the (expensive)
  Argon2id hash run *before* the insert on every request, so the duplicate path
  costs about the same as the success path and does not leak the answer through
  timing.

### Layering (where the logic lives)

The registration flow is split so each layer has one job:

- **Repository** (`app/repositories`): data access only. It `add`s and `flush`es
  but **never commits** — it does not own the transaction.
- **Service** (`app/services`): the use case. It orchestrates policy + hashing +
  repository and **owns the transaction** (`commit`/`rollback`).
- **Boundary** (`app/api`, `app/web`): HTTP only. It parses input, calls the
  service, and renders the result. It contains no business logic; a raised
  `PasswordPolicyError` is turned into the uniform `{error: {code, message}}`
  JSON shape by an app-level handler, or re-rendered into the form for the HTML
  page.

## Threats addressed

- **Offline cracking after a database breach.** A slow, memory-hard hash raises
  the attacker's cost per guess by orders of magnitude, turning "crack the whole
  table overnight" into "infeasible."
- **Rainbow tables / precomputation.** Defeated by a unique per-hash salt.
- **Cross-account password correlation.** A breach cannot reveal which users
  share a password, again thanks to the per-hash salt.
- **Timing side channels.** Comparing the derived key with `hmac.compare_digest`
  (constant time) instead of `==` prevents an attacker from learning how many
  leading bytes matched by measuring response time.
- **CPU-exhaustion denial of service.** The PBKDF2 verifier bounds the iteration
  count read from a stored string, so a crafted or corrupted record cannot force
  an unbounded computation.
- **Algorithm obsolescence.** `needs_rehash` + verify-then-rehash provide a
  transparent upgrade path as parameters and algorithms age.
- **Credential stuffing / dictionary attacks.** Rejecting common and breached
  passwords via a denylist blocks the guesses these attacks make first — far more
  effective than composition rules.
- **Hashing-cost DoS from oversized input.** The maximum-length cap prevents an
  attacker from submitting a huge password to force expensive hashing.
- **Account enumeration via registration.** A neutral, identical response for new
  and existing emails prevents an attacker from harvesting which addresses have
  accounts.
- **TOCTOU race on duplicate emails.** Relying on the database UNIQUE constraint
  (attempt-and-catch) rather than a check-then-insert eliminates the window where
  two concurrent signups could both believe an email is free.

## Design decisions

- **Hand-roll PBKDF2, but use a library for Argon2id.** The point of writing
  PBKDF2 by hand is to make the mechanics (salt, iterations, storage format,
  constant-time compare) concrete. You never hand-roll the Argon2 *primitive* —
  that would be reckless — but you *do* own the framing and the upgrade flow
  around it, which is where the real design lives.
- **The storage string is self-describing.** Chosen precisely so verification is
  parameter-free and so raising costs never breaks old hashes (see Concepts).
- **Read parameters from the stored hash, not from module constants.** The module
  constants describe how to make a *new* hash; an *old* hash must be verified
  with its own recorded parameters.
- **Dispatch by the leading prefix.** The prefix doubles as both the algorithm
  tag and the routing key, which is why PBKDF2's format was designed with a
  leading `pbkdf2_sha256$` and Argon2 uses the PHC `$argon2id$` convention.
- **`needs_rehash` compares embedded parameters against the configured hasher.**
  A freshly made Argon2id hash embeds today's parameters, so it matches and
  needs no rehash; a hash made with weaker parameters embeds different numbers
  and is flagged. The same function also flags every legacy PBKDF2 hash.
- **Upgrade during login, not in a batch job.** The rehash must happen at
  verify-time because that is the *only* moment the server holds the plaintext.
  You cannot rehash the users table offline — you do not have anyone's password.
- **OWASP parameters, pinned as named constants.** PBKDF2 `t=600000`; Argon2id
  `m=19456 KiB, t=2, p=1`. Named constants keep the "current standard" in one
  place, which is exactly what `needs_rehash` measures against.
- **No composition rules, on purpose.** Following NIST 800-63B: length plus a
  common-password denylist, and explicitly *not* "one upper, one digit, one
  symbol." The absence of those rules is a deliberate security decision, not an
  omission.
- **The denylist is embedded and injectable.** `authcore` does no filesystem I/O,
  so the list ships as a casefolded `frozenset` literal rather than a runtime file
  read; `check_password` takes it as a parameter so tests (and future callers) can
  substitute their own without touching the logic.
- **Length is checked before the denylist.** The first failure reported is the
  most fundamental one, so a short-and-common password is reported as too short.
- **The policy raises a coded domain error.** `PasswordPolicyError(code, message)`
  maps directly onto the API's `{error: {code, message}}` shape, so the boundary
  layer never has to parse or re-derive the reason from a string.
- **Duplicate emails are handled by the database, not the application.** The
  service attempts the insert and catches `IntegrityError`, which is both neutral
  (no enumeration) and race-free (no TOCTOU). A `get_by_email` pre-check would be
  neither.
- **Repositories never commit; services own the transaction.** This keeps the
  unit of work in one place, so a service can validate, insert, and either commit
  atomically or roll back cleanly on a collision.
- **Email is normalised (trim + lowercase) before storage.** Addresses are stored
  in one canonical form so the UNIQUE constraint actually prevents duplicates that
  differ only in case or surrounding whitespace.

## References

- [OWASP — Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [NIST SP 800-63B — Digital Identity Guidelines (Authentication)](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [RFC 8018 — PKCS #5: PBKDF2](https://www.rfc-editor.org/rfc/rfc8018)
- [RFC 9106 — Argon2](https://www.rfc-editor.org/rfc/rfc9106)
- [PHC string format specification](https://github.com/P-H-C/phc-string-format/blob/master/phc-sf-spec.md)
- [argon2-cffi documentation](https://argon2-cffi.readthedocs.io/)
- [The Copenhagen Book — Password authentication](https://thecopenhagenbook.com/password-authentication)

## Self-check questions

1. Why does a per-hash salt make two identical passwords produce different stored
   strings, and why does that matter beyond rainbow-table defense?
2. When verifying a password, why must the iteration count and salt be read from
   the stored string rather than from the current module constants?
3. Why is `hmac.compare_digest` used instead of `==` when comparing the derived
   key against the stored one?
4. A freshly created Argon2id hash returns `needs_rehash() == False`, but one
   created with weaker parameters returns `True`. What exactly is being compared,
   and where do the "weaker parameters" come from?
5. Why is PBKDF2 hand-rolled in this project while Argon2id is delegated to a
   library — and where is the line between "the primitive" and "the design"?
6. Why must the verify-then-rehash upgrade happen during login rather than in a
   background job that walks the users table?
7. Why does NIST 800-63B recommend *against* composition rules ("one uppercase,
   one digit, one symbol"), and what is recommended instead?
8. The maximum password length is 128. Give the real reason for an upper bound —
   it is not "longer passwords are weaker."
9. Why is the common-password denylist embedded as a Python `frozenset` and passed
   as a parameter, rather than read from a file inside `check_password`?
10. Why does registration return an identical response for a new email and an
    already-registered one, and what would leak if it did not?
11. Why is a duplicate email handled by catching the database's `IntegrityError`
    rather than by first checking whether the email exists? Name the race this
    avoids.
12. In the registration flow, why must the repository not call `commit()` and the
    service must?

Answers: [`answers/01-passwords.md`](answers/01-passwords.md).

## Exercises

Hands-on coding exercises that extend this module live in
[`../../exercises/01-passwords/`](../../exercises/01-passwords/): completable `.py`
stubs with their own tests and reference solutions. They cover adding a third
hash algorithm to the dispatch, a context-aware password rule (and where it
belongs), and packaging verify-then-rehash as a pure orchestrator. Run them with
`uv run pytest exercises/01-passwords`.
