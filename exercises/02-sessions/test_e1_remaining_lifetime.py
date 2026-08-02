from datetime import UTC, datetime, timedelta

from authcore.sessions import IDLE_TIMEOUT, absolute_expiry
from e1_remaining_lifetime import remaining_lifetime

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_fresh_session_is_bounded_by_the_idle_deadline() -> None:
    # Fresh session: idle deadline (NOW + IDLE_TIMEOUT) is sooner than the
    # absolute one (NOW + ABSOLUTE_LIFETIME), so that is what remains.
    result = remaining_lifetime(NOW, expires_at=absolute_expiry(NOW), last_used_at=NOW)

    assert result == IDLE_TIMEOUT


def test_absolute_deadline_wins_when_sooner() -> None:
    result = remaining_lifetime(
        NOW, expires_at=NOW + timedelta(hours=1), last_used_at=NOW
    )

    assert result == timedelta(hours=1)


def test_already_past_absolute_deadline_gives_zero() -> None:
    result = remaining_lifetime(
        NOW, expires_at=NOW - timedelta(days=1), last_used_at=NOW
    )

    assert result == timedelta(0)


def test_idle_expired_gives_zero() -> None:
    result = remaining_lifetime(
        NOW,
        expires_at=NOW + timedelta(days=365),
        last_used_at=NOW - IDLE_TIMEOUT - timedelta(seconds=1),
    )

    assert result == timedelta(0)
