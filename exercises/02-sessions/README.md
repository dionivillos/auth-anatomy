# Exercises — 02 Sessions from scratch

Hands-on coding exercises that **extend** this module. You implement each in a
plain `.py` file and make its test pass. This directory is kept out of the
project's ruff / mypy / CI test runs, so run it explicitly.

## Layout — what to touch and what not

| Path | What it is | Edit it? |
|---|---|---|
| `eN_*.py` (e.g. `e1_remaining_lifetime.py`) | **The exercise you work on.** Implement here, run the tests, commit your solution. | ✅ **Yes** |
| `test_eN_*.py` | The tests — your target. | ❌ No |
| `starter/eN_*.py` | Read-only copy of the **original prompt** (the untouched stub). Look here to see the task fresh, or to reset. | ❌ No |
| `solutions/eN_*.py` | A **reference solution** (one valid approach — not the only one). | ❌ No |

## How to run the tests

From the repository root:

```bash
# one exercise
uv run pytest exercises/02-sessions/test_e1_remaining_lifetime.py -v

# all of them
uv run pytest exercises/02-sessions -v
```

## How to do an exercise

1. Open the exercise file (e.g. `e1_remaining_lifetime.py`) and read its docstring
   — it states the task and gives step-by-step hints. The same untouched prompt is
   in `starter/` if you want to see it clean again.
2. Replace the `raise NotImplementedError` body with your implementation.
3. Run its test until it goes green, then commit your solution.

To redo an exercise from scratch later:
`cp exercises/02-sessions/starter/e1_remaining_lifetime.py exercises/02-sessions/e1_remaining_lifetime.py`.

## The exercises

### E1 — Remaining session lifetime — ★★☆
`e1_remaining_lifetime.py`. Compute the time left before a session expires — the
sooner of the absolute and idle deadlines, never negative. Reinforces the
two-deadline model.

### E2 — Reject junk cookies before a DB lookup — ★★☆
`e2_looks_like_token.py`. A cheap structural check that a value is shaped like one
of our tokens (32 base32 characters) before hashing it and hitting the database.
Reinforces the token format.

### E3 — Validity + token rotation in one decision — ★★★
`e3_session_rotation.py`. A pure function returning both whether a session is
valid and whether its token is due to rotate (defence-in-depth against long-lived
tokens). Reinforces composing pure rules — the shape of module 01's
verify-then-rehash orchestrator, applied to sessions.

## Further ideas (no scaffolding provided)

- Add **absolute IP/user-agent binding**: reject a session whose request comes
  from a wildly different context than where it was created, and think about the
  false-positive cost (mobile networks, rotating IPs).
- Implement **"log out my other sessions"**: revoke every session for a user
  *except* the current one (needs the current session's id).
