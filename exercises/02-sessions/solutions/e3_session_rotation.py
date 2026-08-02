"""Reference solution — Exercise 3 (validity + rotation decision)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from authcore import sessions as rules

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
    valid = not rules.is_expired(now, expires_at=expires_at, last_used_at=last_used_at)
    should_rotate = valid and (now - last_rotated_at >= ROTATE_EVERY)
    return SessionDecision(valid=valid, should_rotate=should_rotate)
