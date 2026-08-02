"""Exercise 1 — How long until a session expires?

Difficulty: ★★☆

The module decides *whether* a session is expired (`authcore.sessions.is_expired`).
Here you compute *how much time is left* before it expires — useful for a
"your session expires in N minutes" banner, or to decide whether to proactively
refresh.

A session dies at the sooner of its two deadlines:
  - the absolute deadline `expires_at`, and
  - the idle deadline `last_used_at + IDLE_TIMEOUT`.

Return the time from `now` until that sooner deadline, and never a negative value
(an already-expired session has zero remaining).

Complete `remaining_lifetime` so `test_e1_remaining_lifetime.py` passes.
Reference solution: `solutions/e1_remaining_lifetime.py`.
"""

from datetime import datetime, timedelta

from authcore.sessions import IDLE_TIMEOUT


def remaining_lifetime(
    now: datetime, *, expires_at: datetime, last_used_at: datetime
) -> timedelta:
    """Time left before the session expires; `timedelta(0)` if already expired.

    TODO(you):
      1. Compute the idle deadline: `last_used_at + IDLE_TIMEOUT`.
      2. The effective deadline is the earlier of that and `expires_at` (use
         `min`).
      3. Return `deadline - now`, but clamped to at least `timedelta(0)` (use
         `max(..., timedelta(0))`).
    """
    raise NotImplementedError
