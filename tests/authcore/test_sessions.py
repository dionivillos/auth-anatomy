from datetime import UTC, datetime, timedelta

from authcore import sessions

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_absolute_expiry_is_created_at_plus_lifetime() -> None:
    assert sessions.absolute_expiry(NOW) == NOW + sessions.ABSOLUTE_LIFETIME


def test_fresh_session_is_not_expired() -> None:
    expires_at = sessions.absolute_expiry(NOW)

    assert sessions.is_expired(NOW, expires_at=expires_at, last_used_at=NOW) is False


def test_active_session_within_both_deadlines_is_valid() -> None:
    created = NOW
    expires_at = sessions.absolute_expiry(created)
    # Used an hour ago, well within the idle window and the absolute lifetime.
    last_used = NOW - timedelta(hours=1)

    assert sessions.is_expired(NOW, expires_at=expires_at, last_used_at=last_used) is False


def test_expired_by_absolute_deadline_even_if_recently_used() -> None:
    # Past the absolute deadline, but used one second ago.
    expires_at = NOW - timedelta(seconds=1)
    last_used = NOW

    assert sessions.is_expired(NOW, expires_at=expires_at, last_used_at=last_used) is True


def test_expired_by_idle_timeout_even_if_absolute_deadline_is_far() -> None:
    # Absolute deadline far in the future, but unused past the idle timeout.
    expires_at = NOW + timedelta(days=365)
    last_used = NOW - sessions.IDLE_TIMEOUT - timedelta(seconds=1)

    assert sessions.is_expired(NOW, expires_at=expires_at, last_used_at=last_used) is True


def test_absolute_deadline_boundary_counts_as_expired() -> None:
    expires_at = NOW
    last_used = NOW

    assert sessions.is_expired(NOW, expires_at=expires_at, last_used_at=last_used) is True


def test_idle_deadline_boundary_counts_as_expired() -> None:
    expires_at = NOW + timedelta(days=365)
    last_used = NOW - sessions.IDLE_TIMEOUT

    assert sessions.is_expired(NOW, expires_at=expires_at, last_used_at=last_used) is True
