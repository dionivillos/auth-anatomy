"""Session expiry rules (pure: no persistence, no I/O).

A session has two independent deadlines:

  - an ABSOLUTE lifetime: it dies a fixed time after creation, however actively
    it is used. This caps the useful life of a stolen long-lived session.
  - an IDLE timeout (sliding): it dies if left unused for this long. Each use
    slides the window forward by moving `last_used_at` to now.

The database stores `expires_at` (the absolute deadline, fixed at creation) and
`last_used_at` (moved forward on every use). These functions decide the deadline
and validity from plain datetimes; persistence lives in the app layer.

All datetimes are timezone-aware UTC.
"""

from datetime import datetime, timedelta

# Tunable policy. IDLE_TIMEOUT must be shorter than ABSOLUTE_LIFETIME, otherwise
# the idle rule could never fire before the absolute one.
ABSOLUTE_LIFETIME = timedelta(days=30)
IDLE_TIMEOUT = timedelta(days=14)


def absolute_expiry(created_at: datetime) -> datetime:
    """The absolute deadline to store as `expires_at` when creating a session."""
    return created_at + ABSOLUTE_LIFETIME


def is_expired(now: datetime, *, expires_at: datetime, last_used_at: datetime) -> bool:
    """Return True if the session is no longer valid at `now`.

    A session is expired when EITHER deadline has been reached:
      - the absolute deadline `expires_at`, or
      - the idle deadline `last_used_at + IDLE_TIMEOUT`.

    `>=` is used so the exact deadline instant counts as expired.
    """
    return (now >= expires_at) or (now >= last_used_at + IDLE_TIMEOUT)
