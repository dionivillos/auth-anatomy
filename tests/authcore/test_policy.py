import pytest

from authcore.exceptions import PasswordPolicyError
from authcore.policy import MAX_LENGTH, MIN_LENGTH, check_password


def test_a_reasonable_passphrase_is_accepted() -> None:
    # An acceptable password simply returns without raising.
    check_password("a-perfectly-fine-passphrase")


def test_minimum_length_boundary_is_accepted() -> None:
    assert len("correct8") == MIN_LENGTH
    check_password("correct8")  # must not raise


def test_maximum_length_boundary_is_accepted() -> None:
    check_password("a" * MAX_LENGTH)  # must not raise


def test_too_short_is_rejected() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password("abc1234")  # 7 characters

    assert exc_info.value.code == "password_too_short"


def test_empty_password_is_rejected_as_too_short() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password("")

    assert exc_info.value.code == "password_too_short"


def test_too_long_is_rejected() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password("a" * (MAX_LENGTH + 1))

    assert exc_info.value.code == "password_too_long"


def test_common_password_is_rejected() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password("password")

    assert exc_info.value.code == "password_too_common"


@pytest.mark.parametrize("variant", ["PASSWORD", "Password", "PaSsWoRd"])
def test_common_password_check_is_case_insensitive(variant: str) -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password(variant)

    assert exc_info.value.code == "password_too_common"


def test_length_is_checked_before_denylist() -> None:
    # "123456" is both too short and common; the length failure must win.
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password("123456")

    assert exc_info.value.code == "password_too_short"


def test_error_carries_code_and_message() -> None:
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password("qwerty")  # too short (6)

    assert exc_info.value.code == "password_too_short"
    assert isinstance(exc_info.value.message, str)
    assert exc_info.value.message


def test_denylist_is_injectable() -> None:
    custom = frozenset({"unicorn1"})

    # The injected word is rejected...
    with pytest.raises(PasswordPolicyError) as exc_info:
        check_password("unicorn1", denylist=custom)
    assert exc_info.value.code == "password_too_common"

    # ...and a default-common password is now accepted, proving the default was
    # replaced rather than merged.
    check_password("password", denylist=custom)  # must not raise
