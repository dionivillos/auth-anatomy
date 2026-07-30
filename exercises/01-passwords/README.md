# Exercises — 01 Passwords & registration

Hands-on coding exercises that **extend** the module. You implement each in a
plain `.py` file and make its test pass. This directory is intentionally kept out
of the project's ruff / mypy / CI test runs, so it never affects the main build —
run it explicitly.

## Layout — what to touch and what not

| Path | What it is | Edit it? |
|---|---|---|
| `eN_*.py` (e.g. `e1_scrypt_dispatch.py`) | **The exercise you work on.** Implement here, run the tests, commit your solution. | ✅ **Yes** |
| `test_eN_*.py` | The tests — your target. | ❌ No |
| `starter/eN_*.py` | Read-only copy of the **original prompt** (the untouched stub). Look here to see the task fresh, or to reset. | ❌ No |
| `solutions/eN_*.py` | A **reference solution** (one valid approach — not the only one). | ❌ No |

The `eN_*.py` files at the top level are the ones you edit and commit. Everything
in `starter/` and `solutions/` is reference material.

## How to run the tests

From the repository root:

```bash
# one exercise
uv run pytest exercises/01-passwords/test_e1_scrypt_dispatch.py -v

# all of them
uv run pytest exercises/01-passwords -v
```

## How to do an exercise

1. Open the exercise file (e.g. `e1_scrypt_dispatch.py`) and read its docstring —
   it states the task and gives step-by-step hints. The same untouched prompt is
   in `starter/` if you ever want to see it clean again.
2. Replace the `raise NotImplementedError` bodies with your implementation.
3. Run its test until it goes green.
4. Commit your solution — the whole point is that your repository records that you
   did the exercise.

Want to redo an exercise later from scratch? Copy the original back over your
solution:

```bash
cp exercises/01-passwords/starter/e1_scrypt_dispatch.py exercises/01-passwords/e1_scrypt_dispatch.py
```

## The exercises

### E1 — Add a third algorithm (scrypt) to the dispatch — ★★☆
`e1_scrypt_dispatch.py`. Implement scrypt hashing/verification with a
self-describing format, and a `verify_any` that routes scrypt hashes to your
verifier and everything else back to `authcore.passwords.verify_password`.
Reinforces: self-describing formats, prefix dispatch, constant-time compare.

### E2 — Reject passwords containing the user's identifiers — ★★☆
`e2_identifier_policy.py`. Add a context-aware rule on top of the pure base
policy, rejecting passwords that contain the user's email local-part or a word of
their display name. The real lesson is **where** the rule belongs: not in the pure
`authcore.policy`, but one layer out where request context exists.
Reinforces: layering, the purity boundary, composing rather than reimplementing.

### E3 — A pure verify-then-rehash orchestrator — ★★★
`e3_verify_then_rehash.py`. Package the login-time flow as a single pure function
returning an `AuthResult` with the outcome and an optional upgraded hash to
persist. Reinforces: `needs_rehash`, verify-then-rehash, keeping side effects at
the edges.

## Further ideas (no scaffolding provided)

- Add an **application pepper**: HMAC the password with a server-side secret key
  before hashing, so a database leak alone is not enough to start cracking. Keep
  the key injected, and think about key rotation.
- Break neutrality on purpose: make registration return `409` on a duplicate
  email, write a test that fails because of the resulting account enumeration,
  then restore the neutral response.
