from datetime import UTC, datetime, timedelta

from authcore.sessions import absolute_expiry
from e3_session_rotation import ROTATE_EVERY, SessionDecision, evaluate_session

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_fresh_session_is_valid_and_not_due_for_rotation() -> None:
    decision = evaluate_session(
        NOW, expires_at=absolute_expiry(NOW), last_used_at=NOW, last_rotated_at=NOW
    )

    assert decision == SessionDecision(valid=True, should_rotate=False)


def test_valid_session_past_the_rotation_interval_should_rotate() -> None:
    decision = evaluate_session(
        NOW,
        expires_at=absolute_expiry(NOW),
        last_used_at=NOW,
        last_rotated_at=NOW - ROTATE_EVERY,
    )

    assert decision.valid is True
    assert decision.should_rotate is True


def test_expired_session_is_never_rotated() -> None:
    decision = evaluate_session(
        NOW,
        expires_at=NOW - timedelta(days=1),
        last_used_at=NOW - timedelta(days=1),
        last_rotated_at=NOW - ROTATE_EVERY * 10,
    )

    assert decision.valid is False
    assert decision.should_rotate is False
