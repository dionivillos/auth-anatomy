"""Exercise 3 — Validity and token rotation in one pure decision.

Difficulty: ★★★

Issuing a new session id at login defeats fixation, but a long-lived session
still keeps the same token for its whole life. A defence-in-depth technique is to
**rotate** the token periodically: while the session stays valid, occasionally
issue a fresh token id and retire the old one, shrinking the window in which a
leaked-but-idle token is useful.

Package the per-request decision as a single pure function returning both facts:
is the session still valid, and (if so) is it due for a rotation? This mirrors
the verify-then-rehash orchestrator from module 01 — pure logic, side effects
left to the caller.

Complete `evaluate_session` so `test_e3_session_rotation.py` passes.
Reference solution: `solutions/e3_session_rotation.py`.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from authcore import sessions as rules

# How often a valid session's token should be rotated.
ROTATE_EVERY = timedelta(days=1)


@dataclass(frozen=True)
class SessionDecision:
    valid: bool
    should_rotate: bool


def evaluate_session(
    now: datetime,
    *,
    expires_at: datetime,
    last_used_at: datetime,
    last_rotated_at: datetime,
) -> SessionDecision:
    """Decide whether the session is valid and whether its token is due to rotate.

    TODO(you):
      1. `valid` = the session is NOT expired. Reuse the module's rule:
         `not rules.is_expired(now, expires_at=expires_at, last_used_at=last_used_at)`.
      2. `should_rotate` = the session is valid AND it has been at least
         `ROTATE_EVERY` since `last_rotated_at` (i.e. `now - last_rotated_at >=
         ROTATE_EVERY`). An invalid session is never rotated.
      3. Return `SessionDecision(valid=..., should_rotate=...)`.
    """
    if not rules.is_expired(now, expires_at=expires_at, last_used_at=last_used_at):
        return SessionDecision(valid=True, should_rotate=now - last_rotated_at >= ROTATE_EVERY)
    return SessionDecision(valid=False, should_rotate=False)
