"""Reference solution — Exercise 1 (remaining lifetime)."""

from datetime import datetime, timedelta

from authcore.sessions import IDLE_TIMEOUT


def remaining_lifetime(
    now: datetime, *, expires_at: datetime, last_used_at: datetime
) -> timedelta:
    deadline = min(expires_at, last_used_at + IDLE_TIMEOUT)
    return max(deadline - now, timedelta(0))
