import pytest

from authcore.exceptions import PasswordPolicyError
from e2_identifier_policy import IDENTIFIER_IN_PASSWORD, check_password_with_context

CTX = {"email": "alice@example.com", "display_name": "Alice Cooper"}


def test_accepts_a_password_unrelated_to_identifiers() -> None:
    check_password_with_context("a-perfectly-fine-passphrase", **CTX)  # must not raise


def test_base_policy_still_applies_short() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password_with_context("short", **CTX)
    assert exc_info.value.code == "password_too_short"


def test_base_policy_still_applies_common() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password_with_context("password", **CTX)
    assert exc_info.value.code == "password_too_common"


def test_rejects_password_containing_email_local_part() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password_with_context("alice-summer-2024", **CTX)
    assert exc_info.value.code == IDENTIFIER_IN_PASSWORD


def test_rejects_password_containing_display_name() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password_with_context("my-cooper-passphrase", **CTX)
    assert exc_info.value.code == IDENTIFIER_IN_PASSWORD


def test_identifier_check_is_case_insensitive() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password_with_context("xxALICExx-longenough", **CTX)
    assert exc_info.value.code == IDENTIFIER_IN_PASSWORD


def test_short_identifiers_do_not_cause_false_rejections() -> None:
    # A 2-letter display name must not reject every password containing those
    # two letters.
    check_password_with_context(
        "a-perfectly-fine-passphrase", email="al@example.com", display_name="Al"
    )  # must not raise
